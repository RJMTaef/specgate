import subprocess
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from specgate import piv
from specgate.audit import AuditLog
from specgate.screening import app
from specgate.service import Pipeline
from tests.conftest import FEATURE


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1",
        "http://example.com",
        "file:///etc/passwd",
        "http://user:pass@localhost",
        "http://localhost/health",
        "http://localhost?x=y",
        "http://localhost#fragment",
    ],
)
def test_reject_nonlocal_origins(url):
    with pytest.raises(ValueError):
        piv.local_url(url)


def test_piv_success_all_ac_audited(repo, monkeypatch):
    monkeypatch.setattr(piv.httpx, "Client", lambda **_: TestClient(app))
    result = Pipeline(repo).run_piv(FEATURE, "http://localhost")
    assert result["status"] == "passed"
    assert len(result["results"]) == 6
    events = AuditLog(repo / ".specgate/audit.sqlite").events()
    assert len([e for e in events if e["action"] == "piv.check"]) == 6


def failing_client(monkeypatch):
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.request.side_effect = httpx.ConnectError("offline")
    monkeypatch.setattr(piv.httpx, "Client", lambda **_: client)


def test_failure_persists_until_human_rejects(repo, monkeypatch):
    failing_client(monkeypatch)
    rollback = Mock()
    monkeypatch.setattr(piv, "rollback", rollback)
    result = piv.run_piv(repo, FEATURE, "http://127.0.0.1:8000")
    assert result["status"] == "awaiting_approval"
    rollback.assert_not_called()
    # A different invocation reconstructs the graph from SQLite and rejects the proposal.
    assert piv.resume_piv(repo, result["run_id"], False)["status"] == "rejected"
    rollback.assert_not_called()
    with pytest.raises(ValueError, match="not waiting"):
        piv.resume_piv(repo, result["run_id"], True)


@pytest.mark.parametrize(
    "outcome", [True, False, FileNotFoundError(), subprocess.TimeoutExpired("kubectl", 60)]
)
def test_only_explicit_approval_can_request_rollback(repo, monkeypatch, outcome):
    failing_client(monkeypatch)
    rollback = (
        Mock(side_effect=outcome) if isinstance(outcome, Exception) else Mock(return_value=outcome)
    )
    monkeypatch.setattr(piv, "rollback", rollback)
    result = piv.run_piv(repo, FEATURE, "http://localhost/")
    rollback.assert_not_called()
    resumed = piv.resume_piv(repo, result["run_id"], True)
    assert resumed["status"] == ("rollback_requested" if outcome is True else "rollback_failed")
    rollback.assert_called_once_with()


def test_fixed_rollback_target(monkeypatch):
    run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(piv.subprocess, "run", run)
    assert piv.rollback()
    assert run.call_args.args[0] == [
        "kubectl",
        "--context",
        "kind-specgate",
        "-n",
        "specgate",
        "rollout",
        "undo",
        "deployment/screening",
    ]


def test_invalid_or_unknown_run(repo):
    with pytest.raises(ValueError, match="identifier"):
        piv.resume_piv(repo, "../escape", True)
