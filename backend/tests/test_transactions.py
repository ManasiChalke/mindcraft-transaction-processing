import uuid

from tests.conftest import wait_for_terminal


def txn_id():
    return f"TXN-{uuid.uuid4().hex[:12]}"


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "queue_size" in body


def test_valid_credit(client):
    tid = txn_id()
    resp = client.post(
        "/transactions",
        json={"transaction_id": tid, "customer_id": "CUST001", "amount": 1000, "currency": "INR", "type": "CREDIT"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] in ("RECEIVED", "SUCCESS")

    final = wait_for_terminal(client, tid)
    assert final["status"] == "SUCCESS"
    assert final["processing_attempts"] == 1


def test_valid_debit(client):
    customer_id = f"CUST-{uuid.uuid4().hex[:8]}"
    fund_id = txn_id()
    client.post(
        "/transactions",
        json={"transaction_id": fund_id, "customer_id": customer_id, "amount": 5000, "currency": "INR", "type": "CREDIT"},
    )
    wait_for_terminal(client, fund_id)

    debit_id = txn_id()
    resp = client.post(
        "/transactions",
        json={"transaction_id": debit_id, "customer_id": customer_id, "amount": 2000, "currency": "INR", "type": "DEBIT"},
    )
    assert resp.status_code == 201
    final = wait_for_terminal(client, debit_id)
    assert final["status"] == "SUCCESS"

    balance = client.get(f"/customers/{customer_id}/balance").json()
    assert balance["balance"] == 3000


def test_invalid_amount(client):
    tid = txn_id()
    resp = client.post(
        "/transactions",
        json={"transaction_id": tid, "customer_id": "CUST001", "amount": -50, "currency": "INR", "type": "CREDIT"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "FAILED"
    assert "greater than zero" in body["failure_reason"]

    resp_zero = client.post(
        "/transactions",
        json={"transaction_id": txn_id(), "customer_id": "CUST001", "amount": 0, "currency": "INR", "type": "CREDIT"},
    )
    assert resp_zero.json()["status"] == "FAILED"


def test_invalid_type(client):
    tid = txn_id()
    resp = client.post(
        "/transactions",
        json={"transaction_id": tid, "customer_id": "CUST001", "amount": 100, "currency": "INR", "type": "TRANSFER"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "FAILED"
    assert "type" in body["failure_reason"].lower()


def test_missing_required_fields_returns_422(client):
    resp = client.post(
        "/transactions",
        json={"customer_id": "CUST001", "amount": 100, "type": "CREDIT"},
    )
    assert resp.status_code == 422


def test_duplicate_transaction_not_applied_twice(client):
    customer_id = f"CUST-{uuid.uuid4().hex[:8]}"
    fund_id = txn_id()
    client.post(
        "/transactions",
        json={"transaction_id": fund_id, "customer_id": customer_id, "amount": 5000, "currency": "INR", "type": "CREDIT"},
    )
    wait_for_terminal(client, fund_id)

    tid = txn_id()
    payload = {"transaction_id": tid, "customer_id": customer_id, "amount": 1000, "currency": "INR", "type": "DEBIT"}
    first = client.post("/transactions", json=payload)
    wait_for_terminal(client, tid)

    second = client.post("/transactions", json=payload)
    assert second.status_code == 201
    assert second.json()["transaction_id"] == first.json()["transaction_id"]

    balance = client.get(f"/customers/{customer_id}/balance").json()
    assert balance["balance"] == 4000


def test_insufficient_balance(client):
    customer_id = f"CUST-{uuid.uuid4().hex[:8]}"
    fund_id = txn_id()
    client.post(
        "/transactions",
        json={"transaction_id": fund_id, "customer_id": customer_id, "amount": 100, "currency": "INR", "type": "CREDIT"},
    )
    wait_for_terminal(client, fund_id)

    tid = txn_id()
    resp = client.post(
        "/transactions",
        json={"transaction_id": tid, "customer_id": customer_id, "amount": 999999, "currency": "INR", "type": "DEBIT"},
    )
    final = wait_for_terminal(client, tid)
    assert final["status"] == "FAILED"
    assert final["failure_reason"] == "Insufficient balance"
    assert final["processing_attempts"] == 1

    balance = client.get(f"/customers/{customer_id}/balance").json()
    assert balance["balance"] == 100


def test_get_transaction_status_not_found(client):
    resp = client.get("/transactions/NOPE-DOES-NOT-EXIST")
    assert resp.status_code == 404


def test_get_balance_not_found(client):
    resp = client.get("/customers/NOPE-CUSTOMER/balance")
    assert resp.status_code == 404


def test_transaction_history_and_pagination(client):
    customer_id = f"CUST-{uuid.uuid4().hex[:8]}"
    ids = []
    for i in range(5):
        tid = txn_id()
        ids.append(tid)
        client.post(
            "/transactions",
            json={"transaction_id": tid, "customer_id": customer_id, "amount": 10 + i, "currency": "INR", "type": "CREDIT"},
        )
    for tid in ids:
        wait_for_terminal(client, tid)

    page1 = client.get(f"/customers/{customer_id}/transactions", params={"page": 1, "page_size": 2}).json()
    assert page1["total"] == 5
    assert len(page1["items"]) == 2
    assert page1["page"] == 1

    page2 = client.get(f"/customers/{customer_id}/transactions", params={"page": 2, "page_size": 2}).json()
    assert len(page2["items"]) == 2

    page3 = client.get(f"/customers/{customer_id}/transactions", params={"page": 3, "page_size": 2}).json()
    assert len(page3["items"]) == 1

    all_ids = {item["transaction_id"] for p in (page1, page2, page3) for item in p["items"]}
    assert all_ids == set(ids)
