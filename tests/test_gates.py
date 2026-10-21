import json
import subprocess

import pytest

from specgate.contracts import Contract, feature_path
from specgate.gates import check_gate, check_task_commits, coverage_errors, validate_spec
from tests.conftest import FEATURE


def report(tmp_path, percent=95):
    path = tmp_path / f"coverage-{percent}.json"
    path.write_text(json.dumps({"totals": {"percent_covered": percent}}))
    return path


def test_positive_gates(repo):
    assert validate_spec(repo, FEATURE)["passed"]
    assert check_gate(repo, "spec")["passed"]
    assert check_gate(repo, "pr", report(repo))["passed"]


@pytest.mark.parametrize("name", ["spec.md", "plan.md", "tasks.md", "acceptance.yaml"])
def test_missing_artifacts(repo, name):
    (repo / "specs" / FEATURE / name).unlink()
    assert not validate_spec(repo, FEATURE)["passed"]


@pytest.mark.parametrize("marker", ["[NEEDS CLARIFICATION: currency]", "TBD", "TODO"])
def test_unresolved_markers(repo, marker):
    path = repo / "specs" / FEATURE / "plan.md"
    path.write_text(path.read_text() + "\n" + marker)
    assert not validate_spec(repo, FEATURE)["passed"]


@pytest.mark.parametrize("replacement", ["## Unrelated Heading", "## Acceptance Criteria"])
def test_empty_acceptance_section(repo, replacement):
    path = repo / "specs" / FEATURE / "spec.md"
    path.write_text("# Feature\n" + replacement + "\nNo measurable criteria.\n")
    assert not validate_spec(repo, FEATURE)["passed"]


def test_duplicate_acceptance_and_tasks(repo):
    path = repo / "specs" / FEATURE / "spec.md"
    path.write_text(path.read_text().replace("AC-002", "AC-001"))
    tasks = repo / "specs" / FEATURE / "tasks.md"
    tasks.write_text(tasks.read_text().replace("T002", "T001"))
    result = validate_spec(repo, FEATURE)
    assert not result["passed"]
    assert len(result["errors"]) >= 2


@pytest.mark.parametrize("text", ["not: the-schema", "checks: [", "feature: other\nchecks: []"])
def test_invalid_yaml_fails_closed(repo, text):
    (repo / "specs" / FEATURE / "acceptance.yaml").write_text(text)
    assert not validate_spec(repo, FEATURE)["passed"]


def test_contract_mapping_mismatch(repo):
    path = repo / "specs" / FEATURE / "acceptance.yaml"
    path.write_text(path.read_text().replace("AC-001", "AC-099"))
    assert not validate_spec(repo, FEATURE)["passed"]


def test_contract_rejects_duplicate_ids():
    check = {
        "id": "AC-001",
        "method": "GET",
        "path": "/health",
        "status": 200,
        "expected": {"status": "ok"},
    }
    with pytest.raises(ValueError, match="unique"):
        Contract.model_validate({"feature": FEATURE, "checks": [check, check]})


@pytest.mark.parametrize("feature", ["../../escape", "001-X", "--evil", "/tmp/001-escape"])
def test_invalid_feature_id(repo, feature):
    with pytest.raises(ValueError):
        feature_path(repo, feature)


def test_feature_symlink_escape(repo, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    (repo / "specs" / "002-escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        feature_path(repo, "002-escape")


def test_missing_or_unchecked_task_links(repo):
    path = repo / "specs" / FEATURE / "tasks.md"
    path.write_text("- [ ] T001 unfinished\n- [x] T002 missing link\n")
    assert len(check_task_commits(repo, FEATURE)) == 2


def test_unreachable_task_commit(repo):
    path = repo / "specs" / FEATURE / "tasks.md"
    path.write_text("- [x] T001 implemented <!-- commit: " + "f" * 40 + " -->\n")
    assert "not reachable" in check_task_commits(repo, FEATURE)[0]


def test_wrong_task_label_and_empty_commit(repo):
    subprocess.run(
        ["git", "-C", str(repo), "commit", "--allow-empty", "-m", "unrelated"],
        check=True,
        capture_output=True,
    )
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    (repo / "specs" / FEATURE / "tasks.md").write_text(
        f"- [x] T001 implemented <!-- commit: {sha} -->\n"
    )
    assert len(check_task_commits(repo, FEATURE)) == 2


def test_coverage_evidence_and_regression(tmp_path):
    assert not coverage_errors(report(tmp_path, 95), report(tmp_path, 94))
    assert coverage_errors(report(tmp_path, 94), report(tmp_path, 95))
    assert coverage_errors(report(tmp_path, 84))
    assert coverage_errors(tmp_path / "absent")
    assert coverage_errors(report(tmp_path, 101))
    broken = tmp_path / "broken.json"
    broken.write_text("{}")
    assert coverage_errors(broken)


def test_fail_closed_without_features_coverage_or_valid_gate(tmp_path):
    assert not check_gate(tmp_path, "spec")["passed"]
    assert not check_gate(tmp_path, "pr")["passed"]
    with pytest.raises(ValueError):
        check_gate(tmp_path, "unknown")


def test_secret_fails_gate(repo):
    (repo / "leak.txt").write_text("ghp_" + "a" * 36)
    result = check_gate(repo, "spec")
    assert not result["passed"]
    assert "Secret detected" in result["errors"][0]
