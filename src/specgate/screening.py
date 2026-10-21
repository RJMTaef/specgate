"""Deterministic demonstration rules. No real customer data or sanctions lists."""

from decimal import Decimal
from typing import Annotated

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="SpecGate Transaction Screening", version="0.1.0")


class Transfer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_id: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[\w-]+$")]
    amount: Annotated[Decimal, Field(gt=0, le=1_000_000_000, max_digits=12, decimal_places=2)]
    currency: Annotated[str, Field(pattern=r"^USD$")]
    destination_country: Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
    beneficiary: Annotated[str, Field(min_length=1, max_length=100, pattern=r".*\S.*")]


class Decision(BaseModel):
    transaction_id: str
    flagged: bool
    reasons: list[str]
    rules_version: str = "demo-v1"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "rules_version": "demo-v1"}


@app.post("/screen", response_model=Decision)
def screen(transfer: Transfer) -> Decision:
    reasons = []
    if transfer.amount >= Decimal("10000"):
        reasons.append("LARGE_TRANSFER")
    # Synthetic policy codes; deliberately not an authoritative country-risk assessment.
    if transfer.destination_country in {"XZ", "ZZ"}:
        reasons.append("DEMO_HIGH_RISK_DESTINATION")
    if transfer.beneficiary.strip().casefold() == "blocked demo entity":
        reasons.append("DEMO_WATCHLIST_MATCH")
    return Decision(transaction_id=transfer.transaction_id, flagged=bool(reasons), reasons=reasons)
