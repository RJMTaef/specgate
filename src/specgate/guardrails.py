"""Conservative local output guard. Never print matched secret values."""

import re
from pathlib import Path

PATTERNS = {
    "private_key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "github_token": r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b",
    "aws_access_key": r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "credential_assignment": (
        r"""(?i)\b(?:api[_-]?key|password|secret|access[_-]?token)\b"""
        r"""\s*[:=]\s*["']?([A-Za-z0-9_+/=-]{16,})"""
    ),
}


def scan(text: str) -> list[str]:
    return [name for name, pattern in PATTERNS.items() if re.search(pattern, text)]


def require_safe(text: str) -> None:
    findings = scan(text)
    if findings:
        raise ValueError("Output blocked by secret guard: " + ", ".join(findings))


def scan_tree(root: Path) -> list[dict[str, str]]:
    """Scan text sources, excluding runtime state and vendored upstream templates."""
    excluded = {".git", ".venv", ".specgate", "__pycache__", ".pytest_cache", ".ruff_cache"}
    findings = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_symlink() or not path.is_file() or excluded.intersection(relative.parts):
            continue
        if path.stat().st_size > 2_000_000:
            raise ValueError(f"File exceeds scan limit: {relative}")
        try:
            content = path.read_text()
        except UnicodeDecodeError:
            continue
        for rule in scan(content):
            findings.append({"path": str(relative), "rule": rule})
    return findings
