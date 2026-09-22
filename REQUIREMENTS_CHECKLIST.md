# Requirements Checklist

Status is only marked PASS where it was actually run/verified (pytest run,
vitest run, or manual `curl`/browser check) during this session — see
[TESTING.md](TESTING.md) for the full test run details.

## 3. Required Backend APIs

| Requirement | Implementation | File | Test | Status |
|---|---|---|---|---|
| `POST /transactions` | `create_transaction` | `backend/app/main.py` | `test_valid_credit`, `test_valid_debit`, `test_invalid_amount`, `test_invalid_type`, `test_duplicate_...`, manual curl | PASS |
| `GET /transactions/{id}` | `get_transaction` | `backend/app/main.py` | `test_get_transaction_status_not_found`, manual curl | PASS |
| `GET /customers/{id}/balance` | `get_balance` | `backend/app/main.py` | `test_get_balance_not_found`, manual curl | PASS |
| `GET /customers/{id}/transactions` (paginated) | `get_customer_transactions` | `backend/app/main.py` | `test_transaction_history_and_pagination` | PASS |
| `GET /health` | `health` | `backend/app/main.py` | `test_health` | PASS |

## 4. Business Rules

| Requirement | Implementation | File | Test | Status |
|---|---|---|---|---|
| Amount > 0; customer_id/transaction_id mandatory | `_validate_basic`, Pydantic `Field(min_length=1)` | `backend/app/service.py`, `backend/app/schemas.py` | `test_invalid_amount`, `test_missing_required_fields_returns_422` | PASS |
| Type must be CREDIT or DEBIT | `_validate_basic` | `backend/app/service.py` | `test_invalid_type` | PASS |
| DEBIT must not make balance negative | balance check under customer lock | `backend/app/service.py::process_transaction` | `test_insufficient_balance`, both concurrency tests | PASS |
| Same transaction_id not applied twice | existence check + unique PK + IntegrityError fallback | `backend/app/service.py::submit_transaction` | `test_duplicate_transaction_not_applied_twice` | PASS |
| Invalid transactions get clear failure status/reason | `failure_reason` field, set synchronously for basic validation | `backend/app/service.py` | `test_invalid_amount`, `test_invalid_type` | PASS |
| API remains responsive during processing | `POST` only validates+inserts+enqueues, never blocks on worker | `backend/app/main.py`, `backend/app/queue_worker.py` | manual curl (sub-second responses while worker processes) | PASS |

## 5. Local Background Processing

| Requirement | Implementation | File | Status |
|---|---|---|---|
| Local/in-memory queue, no hosted broker | `queue.Queue` (Python stdlib) | `backend/app/queue_worker.py` | PASS |
| React → API → Queue → Worker → DB pipeline | full pipeline implemented | `backend/app/*`, `frontend/src/*` | PASS |

## 6. Added Processing Requirements

| Requirement | Implementation | File | Test | Status |
|---|---|---|---|---|
| Multiple transactions submitted while others process | thread pool (`NUM_WORKERS=3`) consuming shared queue | `backend/app/queue_worker.py` | both concurrency tests | PASS |
| Explicit states RECEIVED→PROCESSING→SUCCESS/FAILED | `Transaction.status` transitions | `backend/app/service.py` | `test_valid_credit` (checks RECEIVED then SUCCESS) | PASS |
| Limited retry for transient failures, not for business failures | attempt loop bounded by `MAX_RETRIES`; business failures return immediately | `backend/app/service.py::process_transaction` | `test_retry_succeeds_after_transient_failures`, `test_retry_gives_up_after_max_retries`, `test_insufficient_balance` (attempts==1) | PASS |
| Record processing attempts + latest failure reason | `processing_attempts`, `failure_reason` columns | `backend/app/models.py` | all transaction tests assert these fields | PASS |
| Resubmission while already processing returns existing status | existence check runs before any new processing | `backend/app/service.py::submit_transaction` | `test_duplicate_transaction_not_applied_twice` | PASS |
| Two near-simultaneous debits don't corrupt balance | per-customer `threading.Lock` + single committed transaction | `backend/app/service.py`, `backend/app/queue_worker.py::get_customer_lock` | `test_concurrent_debits_do_not_corrupt_balance`, `test_many_concurrent_debits_never_go_negative` | PASS |

## 7. Testing

| Requirement | Test | Status |
|---|---|---|
| Unit tests for business logic | `test_invalid_amount`, `test_invalid_type`, `test_insufficient_balance` | PASS |
| API tests for major endpoints | `test_transactions.py` (all endpoints) | PASS |
| Duplicate transaction test | `test_duplicate_transaction_not_applied_twice` | PASS |
| Insufficient-balance test | `test_insufficient_balance` | PASS |
| Retry/failure test | `test_retry.py` (2 tests) | PASS |
| Concurrent/near-concurrent debit test | `test_concurrency.py` (2 tests) | PASS |
| Basic frontend test for critical component/flow | `TransactionForm.test.jsx` (4 tests) | PASS |

Full run: **backend 15/15 passed**, **frontend 4/4 passed** (see
[TESTING.md](TESTING.md)).

## 8. Technology Constraints

| Requirement | Status |
|---|---|
| Python backend: FastAPI | PASS — `backend/app/main.py` |
| SQLite or PostgreSQL | PASS — SQLite, `backend/transactions.db` |
| Everything runs locally | PASS — no external services; verified by running both servers on localhost |

## 9. Deliverables

| Deliverable | Location | Status |
|---|---|---|
| Backend and React source code | `backend/`, `frontend/` | DONE |
| README with setup/run instructions | `README.md` | DONE |
| API documentation/examples | `README.md#api-documentation`, Swagger at `/docs` | DONE |
| Database/schema setup | `backend/app/models.py`, auto-created on startup | DONE |
| Automated tests | `backend/tests/`, `frontend/src/tests/` | DONE |
| Short architecture explanation and assumptions | `ARCHITECTURE.md`, `ASSUMPTIONS.md` | DONE |
| Known limitations / production improvements | `ARCHITECTURE.md#known-limitations--production-improvements` | DONE |
| AI usage disclosure | `AI_USAGE.md` (candidate must still attach chat evidence) | DONE (action required — see file) |
