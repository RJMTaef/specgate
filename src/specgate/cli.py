import json
from pathlib import Path

import typer

from specgate import metrics, piv
from specgate.audit import AuditLog
from specgate.guardrails import scan_tree
from specgate.service import Pipeline

app = typer.Typer(no_args_is_help=True)


def emit(value):
    typer.echo(json.dumps(value, indent=2))


@app.command()
def validate(feature: str, root: Path = Path(".")):
    result = Pipeline(root).validate_spec(feature)
    emit(result)
    raise typer.Exit(0 if result["passed"] else 1)


@app.command()
def gate(
    name: str, coverage: Path | None = None, baseline: Path | None = None, root: Path = Path(".")
):
    result = Pipeline(root).check_gate(name, coverage, baseline)
    emit(result)
    raise typer.Exit(0 if result["passed"] else 1)


@app.command()
def status(root: Path = Path(".")):
    emit(Pipeline(root).get_pipeline_status())


@app.command("scan")
def scan_command(root: Path = Path(".")):
    findings = scan_tree(root)
    AuditLog(root / ".specgate" / "audit.sqlite").record("scan", "failed" if findings else "passed")
    emit({"passed": not findings, "findings": findings})
    raise typer.Exit(1 if findings else 0)


@app.command("piv")
def piv_command(
    feature: str = "001-transaction-screening",
    base_url: str = "http://127.0.0.1:8000",
    root: Path = Path("."),
):
    result = Pipeline(root).run_piv(feature, base_url)
    emit(result)
    raise typer.Exit(0 if result["status"] == "passed" else 1)


@app.command("piv-resume")
def piv_resume(run_id: str, approve: bool = False, root: Path = Path(".")):
    if approve:
        typer.confirm("Request rollback of kind-specgate/specgate/screening?", abort=True)
    result = piv.resume_piv(root, run_id, approve)
    emit(result)
    raise typer.Exit(0 if result["status"] in {"rejected", "rollback_requested"} else 1)


@app.command("metrics")
def metrics_command(
    feature: str = "001-transaction-screening",
    pr_created_at: str | None = None,
    root: Path = Path("."),
):
    emit(metrics.summarize(root, feature, pr_created_at))


@app.command("audit")
def audit_command(root: Path = Path(".")):
    emit(AuditLog(root / ".specgate" / "audit.sqlite").events())
