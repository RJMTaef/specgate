import shutil
import subprocess
from pathlib import Path

import pytest

FEATURE = "001-transaction-screening"
PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo(tmp_path):
    shutil.copytree(PROJECT / "specs", tmp_path / "specs")
    for args in (
        ["init", "-b", "main"],
        ["config", "user.name", "Test"],
        ["config", "user.email", "test@example.invalid"],
        ["add", "."],
        ["commit", "-m", "T001 T002 T003 T004 T005 T006 T007 initial implementation"],
    ):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
    sha = subprocess.check_output(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True
    ).strip()
    tasks = tmp_path / "specs" / FEATURE / "tasks.md"
    lines = []
    for line in tasks.read_text().splitlines():
        if line.startswith("- ["):
            line = line.replace("- [ ]", "- [x]")
            # The repository's sample links refer to its implementation; the fixture has its own.
            line = line.split(" <!-- commit:")[0] + f" <!-- commit: {sha} -->"
        lines.append(line)
    tasks.write_text("\n".join(lines) + "\n")
    return tmp_path
