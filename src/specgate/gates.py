"""Fail-closed gates shared by CLI, CI, and the MCP server."""

import json
import re
import subprocess
from pathlib import Path

import yaml

from specgate.contracts import feature_path, load_contract
from specgate.guardrails import scan_tree

TASK = re.compile(r"^- \[([ xX])\] (T\d{3}) .+", re.MULTILINE)


def validate_spec(root: Path, feature: str) -> dict:
    folder = feature_path(root, feature)
    errors = []
    for name in ("spec.md", "plan.md", "tasks.md", "acceptance.yaml"):
        path = folder / name
        if not path.is_file() or not path.read_text().strip():
            errors.append(f"Missing or empty {name}")
    if errors:
        return {"passed": False, "errors": errors}
    spec = (folder / "spec.md").read_text()
    combined = "\n".join((folder / n).read_text() for n in ("spec.md", "plan.md", "tasks.md"))
    if re.search(r"\[NEEDS CLARIFICATION[^\]]*\]|\bTBD\b|\bTODO\b", combined, re.I):
        errors.append("Unresolved clarification or placeholder")
    section = re.search(r"^## Acceptance Criteria\s*\n(.*?)(?=^## |\Z)", spec, re.M | re.S)
    ids = re.findall(r"^- \*\*(AC-\d{3})\*\*: .+", section[1], re.M) if section else []
    if not ids or len(ids) != len(set(ids)):
        errors.append("Acceptance criteria must have unique AC-NNN IDs and descriptions")
    try:
        contract = load_contract(folder / "acceptance.yaml")
        if contract.feature != feature or set(ids) != {c.id for c in contract.checks}:
            errors.append("Smoke checks must map exactly to spec acceptance criteria")
    except (ValueError, OSError, yaml.YAMLError) as exc:
        errors.append(f"Invalid acceptance contract: {type(exc).__name__}")
    tasks = TASK.findall((folder / "tasks.md").read_text())
    if not tasks or len(tasks) != len({task[1] for task in tasks}):
        errors.append("Task list must contain unique TNNN checkboxes")
    return {"passed": not errors, "errors": errors}


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    # Arguments are fixed by gate code or validated full commit hashes; no shell is used.
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *args],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def check_task_commits(root: Path, feature: str) -> list[str]:
    text = (feature_path(root, feature) / "tasks.md").read_text()
    errors = []
    for match in TASK.finditer(text):
        checked, task = match.groups()
        link = re.search(r"<!-- commit: ([0-9a-f]{40}) -->", match[0])
        if checked.lower() != "x" or not link:
            errors.append(f"{task}: must be complete and linked to a full commit SHA")
            continue
        sha = link[1]
        if git(root, "merge-base", "--is-ancestor", sha, "HEAD").returncode:
            errors.append(f"{task}: linked commit is not reachable from HEAD")
            continue
        subject = git(root, "show", "-s", "--format=%B", sha).stdout
        if not re.search(rf"\b{task}\b", subject):
            errors.append(f"{task}: commit message must include the task ID")
        if not git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", sha).stdout:
            errors.append(f"{task}: linked commit contains no file changes")
    return errors


def coverage_errors(report: Path, baseline: Path | None = None) -> list[str]:
    try:
        current = float(json.loads(report.read_text())["totals"]["percent_covered"])
        floor = 85.0
        if baseline:
            floor = max(floor, float(json.loads(baseline.read_text())["totals"]["percent_covered"]))
        if not 0 <= current <= 100 or not 0 <= floor <= 100:
            raise ValueError("Invalid coverage")
        return [] if current + 1e-9 >= floor else [f"Coverage {current:.2f}% is below {floor:.2f}%"]
    except (OSError, KeyError, ValueError, TypeError):
        return ["Missing or invalid coverage evidence"]


def check_gate(
    root: Path, gate: str, coverage: Path | None = None, baseline: Path | None = None
) -> dict:
    if gate not in {"spec", "pr"}:
        raise ValueError("Gate must be spec or pr")
    features = sorted(p.name for p in (root / "specs").glob("[0-9]*") if p.is_dir())
    errors = [] if features else ["No features found"]
    for feature in features:
        result = validate_spec(root, feature)
        errors.extend(f"{feature}: {e}" for e in result["errors"])
        if gate == "pr" and result["passed"]:
            errors.extend(check_task_commits(root, feature))
    if gate == "pr":
        errors.extend(
            coverage_errors(coverage, baseline) if coverage else ["Coverage report required"]
        )
    errors.extend(f"Secret detected: {f['path']} ({f['rule']})" for f in scan_tree(root))
    return {"gate": gate, "passed": not errors, "features": features, "errors": errors}
