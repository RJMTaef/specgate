import asyncio
import json
from datetime import UTC, datetime, timedelta

from specgate.audit import AuditLog
from specgate.mcp_server import create_server
from specgate.metrics import summarize
from tests.conftest import FEATURE


def test_mcp_tool_contract_and_real_dispatch(repo, monkeypatch):
    async def scenario():
        server = create_server(repo)
        names = {tool.name for tool in await server.list_tools()}
        assert names == {
            "validate_spec",
            "check_gate",
            "get_pipeline_status",
            "run_piv",
            "guard_output",
        }
        assert not any("approve" in name or "resume" in name for name in names)
        for name, arguments in [
            ("validate_spec", {"feature": FEATURE}),
            ("check_gate", {"gate": "spec"}),
            ("get_pipeline_status", {}),
            ("guard_output", {"feature": FEATURE, "text": "Safe synthetic review"}),
        ]:
            result = await server.call_tool(name, arguments)
            assert not result.is_error
        monkeypatch.setattr("specgate.service.piv.run_piv", lambda *_: {"status": "passed"})
        assert not (await server.call_tool("run_piv", {"feature": FEATURE})).is_error

    asyncio.run(scenario())


def test_metrics_real_observations_and_missing_lead_time(repo):
    assert summarize(repo, FEATURE)["gate_pass_rate"] is None
    audit = AuditLog(repo / ".specgate/audit.sqlite")
    audit.record("gate.spec", "completed")
    audit.record("gate.pr", "failed")
    audit.record("gate.pr", "error")
    audit.record("gate.pr", "started")
    result = summarize(repo, FEATURE, (datetime.now(UTC) + timedelta(seconds=10)).isoformat())
    assert result["gate_runs"] == 3
    assert result["gate_pass_rate"] == 1 / 3
    assert result["spec_to_pr_seconds"] >= 9
    assert (
        summarize(repo, "999-absent", datetime.now(UTC).isoformat())["spec_to_pr_seconds"] is None
    )
    assert "first spec commit" in json.dumps(result)
