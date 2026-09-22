import threading
import uuid

from tests.conftest import wait_for_terminal


def txn_id():
    return f"TXN-{uuid.uuid4().hex[:12]}"


def test_concurrent_debits_do_not_corrupt_balance(client):
    customer_id = f"CUST-{uuid.uuid4().hex[:8]}"
    fund_id = txn_id()
    client.post(
        "/transactions",
        json={"transaction_id": fund_id, "customer_id": customer_id, "amount": 5000, "currency": "INR", "type": "CREDIT"},
    )
    wait_for_terminal(client, fund_id)

    tid_a = txn_id()
    tid_b = txn_id()
    barrier = threading.Barrier(2)
    results = {}

    def submit(tid):
        barrier.wait()
        resp = client.post(
            "/transactions",
            json={"transaction_id": tid, "customer_id": customer_id, "amount": 4000, "currency": "INR", "type": "DEBIT"},
        )
        results[tid] = resp.status_code

    t1 = threading.Thread(target=submit, args=(tid_a,))
    t2 = threading.Thread(target=submit, args=(tid_b,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    final_a = wait_for_terminal(client, tid_a)
    final_b = wait_for_terminal(client, tid_b)

    statuses = {final_a["status"], final_b["status"]}
    assert statuses == {"SUCCESS", "FAILED"}, f"expected exactly one success/failure pair, got {final_a}, {final_b}"

    failed = final_a if final_a["status"] == "FAILED" else final_b
    assert failed["failure_reason"] == "Insufficient balance"

    balance = client.get(f"/customers/{customer_id}/balance").json()
    assert balance["balance"] == 1000


def test_many_concurrent_debits_never_go_negative(client):
    customer_id = f"CUST-{uuid.uuid4().hex[:8]}"
    fund_id = txn_id()
    client.post(
        "/transactions",
        json={"transaction_id": fund_id, "customer_id": customer_id, "amount": 5000, "currency": "INR", "type": "CREDIT"},
    )
    wait_for_terminal(client, fund_id)

    tids = [txn_id() for _ in range(10)]
    barrier = threading.Barrier(len(tids))

    def submit(tid):
        barrier.wait()
        client.post(
            "/transactions",
            json={"transaction_id": tid, "customer_id": customer_id, "amount": 1000, "currency": "INR", "type": "DEBIT"},
        )

    threads = [threading.Thread(target=submit, args=(tid,)) for tid in tids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    finals = [wait_for_terminal(client, tid) for tid in tids]
    successes = [f for f in finals if f["status"] == "SUCCESS"]
    failures = [f for f in finals if f["status"] == "FAILED"]

    assert len(successes) == 5
    assert len(failures) == 5
    assert all(f["failure_reason"] == "Insufficient balance" for f in failures)

    balance = client.get(f"/customers/{customer_id}/balance").json()
    assert balance["balance"] == 0
