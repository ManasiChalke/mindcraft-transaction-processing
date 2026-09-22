import os
import tempfile

# must run before any app.* import, including other test modules at collection time
_TMP_DIR = tempfile.mkdtemp(prefix="txn_test_")
os.environ["DB_PATH"] = os.path.join(_TMP_DIR, "test.db")
os.environ["TRANSIENT_FAILURE_RATE"] = "0.0"

import time
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def wait_for_terminal(client, transaction_id, timeout=5.0):
    """Polls GET /transactions/{id} until status is SUCCESS/FAILED or timeout."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        resp = client.get(f"/transactions/{transaction_id}")
        if resp.status_code == 200:
            last = resp.json()
            if last["status"] in ("SUCCESS", "FAILED"):
                return last
        time.sleep(0.05)
    raise AssertionError(f"Transaction {transaction_id} did not reach terminal state: {last}")
