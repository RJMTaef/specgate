"""LangGraph PIV with durable interruption and an operator-only recovery command."""

import re
import subprocess
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from specgate.audit import AuditLog
from specgate.contracts import feature_path, load_contract


class State(TypedDict, total=False):
    feature: str
    base_url: str
    results: list[dict]
    status: str
    approved: bool


def local_url(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("PIV requires an HTTP loopback origin without credentials or path")
    return url.rstrip("/")


def rollback() -> bool:
    """Fixed target; never interpolate model output into commands."""
    result = subprocess.run(
        [  # noqa: S607 - fixed operator target; PATH belongs to the local operator
            "kubectl",
            "--context",
            "kind-specgate",
            "-n",
            "specgate",
            "rollout",
            "undo",
            "deployment/screening",
        ],
        capture_output=True,
        timeout=60,
        check=False,
    )
    return result.returncode == 0


def build_graph(root: Path, saver):
    audit = AuditLog(root / ".specgate" / "audit.sqlite")

    def probe(state: State) -> dict:
        contract = load_contract(feature_path(root, state["feature"]) / "acceptance.yaml")
        results = []
        with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as client:
            for check in contract.checks:
                try:
                    response = client.request(
                        check.method, state["base_url"] + check.path, json=check.body
                    )
                    data = response.json()
                    passed = (
                        response.status_code == check.status
                        and isinstance(data, dict)
                        and all(data.get(k) == v for k, v in check.expected.items())
                    )
                except (httpx.HTTPError, ValueError):
                    passed = False
                results.append({"id": check.id, "passed": passed})
                audit.record("piv.check", "passed" if passed else "failed", state["feature"])
        return {
            "results": results,
            "status": "passed" if all(r["passed"] for r in results) else "awaiting_approval",
        }

    def approval(state: State) -> dict:
        decision = interrupt(
            {
                "proposal": "rollback",
                "target": "kind-specgate/specgate/screening",
                "failed": [r["id"] for r in state["results"] if not r["passed"]],
            }
        )
        approved = decision is True
        audit.record("piv.approval", "approved" if approved else "rejected", state["feature"])
        return {"approved": approved, "status": "rollback_approved" if approved else "rejected"}

    def recover(state: State) -> dict:
        try:
            successful = rollback()
        except (OSError, subprocess.TimeoutExpired):
            successful = False
        status = "rollback_requested" if successful else "rollback_failed"
        audit.record("piv.rollback", status, state["feature"])
        return {"status": status}

    graph = StateGraph(State)
    graph.add_node("probe", probe)
    graph.add_node("approval", approval)
    graph.add_node("recover", recover)
    graph.add_edge(START, "probe")
    graph.add_conditional_edges("probe", lambda s: END if s["status"] == "passed" else "approval")
    graph.add_conditional_edges("approval", lambda s: "recover" if s["approved"] else END)
    graph.add_edge("recover", END)
    return graph.compile(checkpointer=saver)


def run_piv(root: Path, feature: str, base_url: str) -> dict:
    url = local_url(base_url)
    load_contract(feature_path(root, feature) / "acceptance.yaml")
    state_dir = root / ".specgate"
    state_dir.mkdir(exist_ok=True)
    run_id = str(uuid4())
    AuditLog(state_dir / "audit.sqlite").record("piv.started", "started", feature)
    with SqliteSaver.from_conn_string(str(state_dir / "piv.sqlite")) as saver:
        graph = build_graph(root, saver)
        result = graph.invoke(
            {"feature": feature, "base_url": url}, {"configurable": {"thread_id": run_id}}
        )
    pauses = result.get("__interrupt__", ())
    return {
        "run_id": run_id,
        "status": result["status"],
        "results": result["results"],
        "approval_request": pauses[0].value if pauses else None,
    }


def resume_piv(root: Path, run_id: str, approved: bool) -> dict:
    if not re.fullmatch(r"[0-9a-f-]{36}", run_id):
        raise ValueError("Invalid run identifier")
    with SqliteSaver.from_conn_string(str(root / ".specgate" / "piv.sqlite")) as saver:
        graph = build_graph(root, saver)
        config = {"configurable": {"thread_id": run_id}}
        snapshot = graph.get_state(config)
        if snapshot.next != ("approval",):
            raise ValueError("Run is not waiting for approval")
        result = graph.invoke(Command(resume=approved), config)
    return {"run_id": run_id, "status": result["status"]}
