# Testing

## Backend — pytest (15 tests, all passing)

Run:

```bash
cd backend
venv\Scripts\activate
pytest -v
```

Test isolation: `tests/conftest.py` points `DB_PATH` at a fresh temp SQLite
file before any `app.*` module is imported, so the suite never touches your
local `transactions.db`. All tests share one `TestClient` (and therefore one
running worker pool) for the session; each test uses unique
`transaction_id`/`customer_id` values to avoid cross-test interference, and
polls `GET /transactions/{id}` until a terminal state instead of sleeping a
fixed amount.

| # | Requirement | Test file / function |
|---|---|---|
| 1 | Health check | `test_transactions.py::test_health` |
| 2 | Valid CREDIT reaches SUCCESS | `test_transactions.py::test_valid_credit` |
| 3 | Valid DEBIT reaches SUCCESS, balance updates | `test_transactions.py::test_valid_debit` |
| 4 | Invalid amount (negative, zero) → FAILED | `test_transactions.py::test_invalid_amount` |
| 5 | Invalid type → FAILED | `test_transactions.py::test_invalid_type` |
| 6 | Missing required fields → 422 | `test_transactions.py::test_missing_required_fields_returns_422` |
| 7 | Duplicate transaction not applied twice | `test_transactions.py::test_duplicate_transaction_not_applied_twice` |
| 8 | Insufficient balance → FAILED, not retried, balance unchanged | `test_transactions.py::test_insufficient_balance` |
| 9 | GET transaction status (found + 404) | `test_transactions.py::test_get_transaction_status_not_found` |
| 10 | GET balance (found + 404) | `test_transactions.py::test_get_balance_not_found` |
| 11 | Transaction history + pagination | `test_transactions.py::test_transaction_history_and_pagination` |
| 12 | Retry then succeed (transient failure) | `test_retry.py::test_retry_succeeds_after_transient_failures` |
| 13 | Retry exhausted → FAILED after MAX_RETRIES | `test_retry.py::test_retry_gives_up_after_max_retries` |
| 14 | Concurrent debits (2-way), no corruption | `test_concurrency.py::test_concurrent_debits_do_not_corrupt_balance` |
| 15 | Concurrent debits (10-way), balance never negative | `test_concurrency.py::test_many_concurrent_debits_never_go_negative` |

The retry tests monkeypatch `app.service._maybe_simulate_transient_failure`
to deterministically fail N times then succeed (test 12), or fail forever
until `MAX_RETRIES` is hit (test 13) — no reliance on random chance.

The concurrency tests use a `threading.Barrier` to fire multiple `POST`
requests as close to simultaneously as possible against the same customer,
then assert the final balance and per-transaction outcomes are exactly what
serialized processing would produce (no double-spend, no lost update,
balance never negative).

## Frontend — vitest + React Testing Library (4 tests, all passing)

Run:

```bash
cd frontend
npm test
```

| Test | Behavior verified |
|---|---|
| Missing required fields | Client-side validation blocks submission; API is never called |
| Valid submission → SUCCESS | Form calls the API, renders the SUCCESS result, calls `onProcessed` |
| Valid submission → FAILED | Renders the failure reason (e.g. "Insufficient balance") |
| API rejects | Network/API errors surface as a visible `role="alert"` message |

`src/api.js` is mocked with `vi.spyOn` so these are true unit tests of
`TransactionForm`'s logic, independent of a running backend.

## Manual end-to-end verification performed

With both servers running locally, the following was exercised directly
against the live API (see commands in [README.md](README.md#api-documentation)):
CREDIT → balance increases; DEBIT → balance decreases; DEBIT exceeding
balance → FAILED, balance unchanged; resubmitting the same `transaction_id`
→ returns the original result, balance unchanged; paginated history reflects
all of the above.
