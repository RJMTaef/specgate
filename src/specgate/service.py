"""Audited facade: all exposed agent operations pass through this boundary."""

from pathlib import Path

from specgate import gates, piv
from specgate.audit import AuditLog
from specgate.contracts import feature_path
from specgate.guardrails import require_safe


class Pipeline:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.audit = AuditLog(self.root / ".specgate" / "audit.sqlite")

    def _call(self, action, operation):
        self.audit.record(action, "started")
        try:
            result = operation()
            require_safe(str(result))
        except Exception:
            self.audit.record(action, "error")
            raise
        self.audit.record(action, "failed" if result.get("passed") is False else "completed")
        return result

    def validate_spec(self, feature: str):
        return self._call("validate_spec", lambda: gates.validate_spec(self.root, feature))

    def check_gate(self, gate: str, coverage: Path | None = None, baseline: Path | None = None):
        return self._call(
            f"gate.{gate}", lambda: gates.check_gate(self.root, gate, coverage, baseline)
        )

    def get_pipeline_status(self):
        return self._call(
            "get_pipeline_status",
            lambda: {
                "spec_ready": gates.check_gate(self.root, "spec"),
                "note": "PR Ready is authoritative only in GitHub Actions after tests and coverage",
            },
        )

    def run_piv(self, feature: str, base_url: str):
        return self._call("run_piv", lambda: piv.run_piv(self.root, feature, base_url))

    def guard_output(self, feature: str, text: str):
        def publish():
            feature_path(self.root, feature)
            require_safe(text)
            folder = self.root / "agent-output" / feature
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "review.md").write_text(text)
            return {"passed": True, "path": str(folder.relative_to(self.root) / "review.md")}

        return self._call("guard_output", publish)
