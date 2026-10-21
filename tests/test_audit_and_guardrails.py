import json
import sqlite3
import subprocess
import sys

import pytest

from specgate.audit import AuditLog
from specgate.guardrails import require_safe, scan, scan_tree
from specgate.service import Pipeline
from tests.conftest import FEATURE, PROJECT


def test_audit_chain_and_tamper_detection(tmp_path):
    log = AuditLog(tmp_path / "audit.sqlite")
    log.record("gate.spec", "completed", FEATURE)
    log.record("piv.check", "passed", FEATURE)
    assert len(log.events()) == 2
    with sqlite3.connect(log.path) as db:
        db.execute("UPDATE events SET body = '{}' WHERE id = 1")
    with pytest.raises(ValueError, match="chain"):
        log.events()


@pytest.mark.parametrize(
    "text",
    [
        "ghp_" + "a" * 36,
        "AKIA" + "A" * 16,
        "-----BEGIN " + "PRIVATE KEY-----",
        "api_key=" + "a" * 30,
    ],
)
def test_secret_patterns_do_not_echo_values(text):
    assert scan(text)
    with pytest.raises(ValueError) as error:
        require_safe(text)
    assert text not in str(error.value)


def test_safe_text_and_scan_exclusions(tmp_path):
    require_safe("No secrets here")
    (tmp_path / "public.md").write_text("safe")
    (tmp_path / "binary.bin").write_bytes(b"\xff")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored").write_text("ghp_" + "a" * 36)
    (tmp_path / "link").symlink_to(tmp_path / ".venv" / "ignored")
    assert scan_tree(tmp_path) == []
    (tmp_path / "large").write_bytes(b"a" * 2_000_001)
    with pytest.raises(ValueError, match="scan limit"):
        scan_tree(tmp_path)


def test_audited_facade_and_output_guard(repo):
    pipeline = Pipeline(repo)
    assert pipeline.validate_spec(FEATURE)["passed"]
    assert pipeline.check_gate("spec")["passed"]
    assert pipeline.get_pipeline_status()["spec_ready"]["passed"]
    assert pipeline.guard_output(FEATURE, "Reviewed synthetic transfer rule")["passed"]
    path = repo / "agent-output" / FEATURE / "review.md"
    original = path.read_text()
    with pytest.raises(ValueError):
        pipeline.guard_output(FEATURE, "ghp_" + "a" * 36)
    assert path.read_text() == original
    assert pipeline.audit.events()[-1]["outcome"] == "error"
    assert not pipeline.check_gate("pr")["passed"]
    assert pipeline.audit.events()[-1]["outcome"] == "failed"


@pytest.mark.parametrize("phase", ["pre", "post"])
def test_claude_hooks_redact_and_record(repo, phase):
    event = {
        "tool_name": "Write",
        "tool_input": {"content": "ghp_" + "a" * 36},
        "tool_response": "ghp_" + "b" * 36,
    }
    result = subprocess.run(
        [sys.executable, str(PROJECT / "scripts/claude-hook.py"), phase],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        cwd=repo,
    )
    assert result.returncode == 2
    assert "ghp_" not in result.stderr
    assert AuditLog(repo / ".specgate/audit.sqlite").events()[-1]["outcome"] == "blocked"
    clean = subprocess.run(
        [sys.executable, str(PROJECT / "scripts/claude-hook.py"), phase],
        input=json.dumps({"tool_name": "Read"}),
        text=True,
        capture_output=True,
        cwd=repo,
    )
    assert clean.returncode == 0
