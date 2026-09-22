import uuid

from app import service
from tests.conftest import wait_for_terminal


def txn_id():
    return f"TXN-{uuid.uuid4().hex[:12]}"


def test_retry_succeeds_after_transient_failures(client, monkeypatch):
    def flaky(attempt):
        if attempt < 3:
            raise service.TransientProcessingError("Simulated downstream timeout")

    monkeypatch.setattr(service, "_maybe_simulate_transient_failure", flaky)

    customer_id = f"CUST-{uuid.uuid4().hex[:8]}"
    fund_id = txn_id()
    client.post(
        "/transactions",
        json={"transaction_id": fund_id, "customer_id": customer_id, "amount": 5000, "currency": "INR", "type": "CREDIT"},
    )
    wait_for_terminal(client, fund_id, timeout=5.0)

    tid = txn_id()
    client.post(
        "/transactions",
        json={"transaction_id": tid, "customer_id": customer_id, "amount": 1000, "currency": "INR", "type": "DEBIT"},
    )
    final = wait_for_terminal(client, tid, timeout=5.0)
    assert final["status"] == "SUCCESS"
    assert final["processing_attempts"] == 3


def test_retry_gives_up_after_max_retries(client, monkeypatch):
    def always_fails(attempt):
        raise service.TransientProcessingError("Simulated permanent downstream outage")

    monkeypatch.setattr(service, "_maybe_simulate_transient_failure", always_fails)

    tid = txn_id()
    client.post(
        "/transactions",
        json={"transaction_id": tid, "customer_id": "CUST002", "amount": 100, "currency": "INR", "type": "CREDIT"},
    )
    final = wait_for_terminal(client, tid, timeout=5.0)
    assert final["status"] == "FAILED"
    assert final["processing_attempts"] == service.MAX_RETRIES
    assert "Max retry attempts exceeded" in final["failure_reason"]
