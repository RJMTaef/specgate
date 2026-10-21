import pytest
from fastapi.testclient import TestClient

from specgate.contracts import load_contract
from specgate.screening import app
from tests.conftest import FEATURE, PROJECT

client = TestClient(app)
VALID = {
    "transaction_id": "test-1",
    "amount": "25.00",
    "currency": "USD",
    "destination_country": "CA",
    "beneficiary": "Demo Person",
}


def test_all_acceptance_criteria_against_api():
    for check in load_contract(PROJECT / "specs" / FEATURE / "acceptance.yaml").checks:
        response = client.request(check.method, check.path, json=check.body)
        assert response.status_code == check.status
        assert all(response.json().get(k) == v for k, v in check.expected.items()), check.id


@pytest.mark.parametrize(
    "updates",
    [
        {"amount": "-1"},
        {"amount": "0"},
        {"amount": "1.001"},
        {"amount": "NaN"},
        {"amount": "Infinity"},
        {"amount": "1000000001"},
        {"currency": "EUR"},
        {"destination_country": "canada"},
        {"transaction_id": ""},
        {"beneficiary": " "},
        {"extra": "unknown"},
    ],
)
def test_reject_invalid_transfer(updates):
    assert client.post("/screen", json=VALID | updates).status_code == 422


def test_boundary_and_multiple_reasons():
    below = client.post("/screen", json=VALID | {"amount": "9999.99"}).json()
    assert below["flagged"] is False
    combined = client.post(
        "/screen",
        json=VALID
        | {
            "amount": "10000.00",
            "destination_country": "ZZ",
            "beneficiary": "  BLOCKED DEMO ENTITY  ",
        },
    ).json()
    assert combined["reasons"] == [
        "LARGE_TRANSFER",
        "DEMO_HIGH_RISK_DESTINATION",
        "DEMO_WATCHLIST_MATCH",
    ]
    assert "beneficiary" not in combined
