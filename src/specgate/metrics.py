"""Observed gate outcomes and spec-to-PR lead time; no fabricated adoption data."""

from datetime import datetime
from pathlib import Path

from specgate.audit import AuditLog
from specgate.gates import git


def summarize(root: Path, feature: str, pr_created_at: str | None = None) -> dict:
    events = AuditLog(root / ".specgate" / "audit.sqlite").events()
    outcomes = [
        e
        for e in events
        if e["action"].startswith("gate.") and e["outcome"] in {"completed", "failed", "error"}
    ]
    passed = sum(e["outcome"] == "completed" for e in outcomes)
    duration = None
    if pr_created_at:
        history = git(
            root, "log", "--diff-filter=A", "--format=%cI", "--", f"specs/{feature}/spec.md"
        ).stdout.splitlines()
        if history:
            duration = max(
                0,
                (
                    datetime.fromisoformat(pr_created_at.replace("Z", "+00:00"))
                    - datetime.fromisoformat(history[-1])
                ).total_seconds(),
            )
    return {
        "gate_runs": len(outcomes),
        "gate_passes": passed,
        "gate_pass_rate": passed / len(outcomes) if outcomes else None,
        "spec_to_pr_seconds": duration,
        "scope": "local audit / this CI run; download artifacts to aggregate across runs",
        "lead_time_definition": "first spec commit to GitHub PR creation",
    }
