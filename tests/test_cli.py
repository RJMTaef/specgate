import json

from typer.testing import CliRunner

from specgate import cli, mcp_server
from tests.conftest import FEATURE

runner = CliRunner()


def test_cli_validation_gates_status_and_audit(repo):
    for args in (
        ["validate", FEATURE],
        ["gate", "spec"],
        ["status"],
        ["scan"],
        ["metrics"],
        ["audit"],
    ):
        result = runner.invoke(cli.app, [*args, "--root", str(repo)])
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)
    failed = runner.invoke(cli.app, ["gate", "pr", "--root", str(repo)])
    assert failed.exit_code == 1
    (repo / "specs" / FEATURE / "plan.md").unlink()
    assert runner.invoke(cli.app, ["validate", FEATURE, "--root", str(repo)]).exit_code == 1
    (repo / "leak.txt").write_text("ghp_" + "a" * 36)
    assert runner.invoke(cli.app, ["scan", "--root", str(repo)]).exit_code == 1


def test_cli_piv_and_approval_prompt(repo, monkeypatch):
    monkeypatch.setattr("specgate.service.piv.run_piv", lambda *_: {"status": "passed"})
    assert runner.invoke(cli.app, ["piv", "--root", str(repo)]).exit_code == 0
    monkeypatch.setattr("specgate.service.piv.run_piv", lambda *_: {"status": "awaiting_approval"})
    assert runner.invoke(cli.app, ["piv", "--root", str(repo)]).exit_code == 1
    decisions = []

    def resume(root, run_id, approved):
        decisions.append(approved)
        return {"status": "rollback_requested" if approved else "rejected"}

    monkeypatch.setattr(cli.piv, "resume_piv", resume)
    assert runner.invoke(cli.app, ["piv-resume", "run", "--root", str(repo)]).exit_code == 0
    assert (
        runner.invoke(
            cli.app, ["piv-resume", "run", "--approve", "--root", str(repo)], input="n\n"
        ).exit_code
        == 1
    )
    assert decisions == [False]
    assert (
        runner.invoke(
            cli.app, ["piv-resume", "run", "--approve", "--root", str(repo)], input="y\n"
        ).exit_code
        == 0
    )
    assert decisions == [False, True]
    monkeypatch.setattr(cli.piv, "resume_piv", lambda *_: {"status": "rollback_failed"})
    assert runner.invoke(cli.app, ["piv-resume", "run", "--root", str(repo)]).exit_code == 1


def test_mcp_entry_point(monkeypatch, tmp_path):
    observed = []

    class Server:
        def run(self):
            observed.append("stdio")

    def create(root):
        observed.append(root)
        return Server()

    monkeypatch.setenv("SPECGATE_ROOT", str(tmp_path))
    monkeypatch.setattr(mcp_server, "create_server", create)
    mcp_server.main()
    assert observed == [tmp_path, "stdio"]
