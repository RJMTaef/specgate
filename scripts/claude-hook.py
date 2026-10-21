"""Claude Code hook: metadata-only audit and secret detection. Input is never echoed."""

import json
import re
import sys
from pathlib import Path

from specgate.audit import AuditLog
from specgate.guardrails import scan


def main():
    event = json.load(sys.stdin)
    phase = sys.argv[1]
    tool = re.sub(r"[^A-Za-z0-9_.-]", "_", str(event.get("tool_name", "unknown")))[:80]
    findings = scan(json.dumps(event.get("tool_input" if phase == "pre" else "tool_response")))
    AuditLog(Path(".specgate/audit.sqlite")).record(
        f"claude.{phase}.{tool}", "blocked" if findings else "observed")
    if findings:
        print("Secret guard blocked tool data: " + ", ".join(findings), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
