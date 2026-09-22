# Architecture

```
React (Vite, :5173)
      │  fetch (JSON over HTTP)
      ▼
FastAPI (Uvicorn, :8000)
      │  POST /transactions → validate → persist (status=RECEIVED) → enqueue → return immediately
      ▼
queue.Queue  (in-memory, single process, no external broker)
      │  worker threads (NUM_WORKERS=3) block on queue.get()
      ▼
Worker thread
      │  acquire per-customer threading.Lock
      │  reload transaction + customer row
      │  re-check business rules against *current* balance
      │  update balance + transaction status in one committed transaction
      │  release lock
      ▼
SQLite (transactions.db)
      customers(customer_id, balance, currency, created_at, updated_at)
      transactions(transaction_id, customer_id, amount, currency, type,
                   status, failure_reason, processing_attempts,
                   created_at, updated_at)
```

FastAPI's request-handling stays synchronous and fast: `POST /transactions`
only does validation + a single insert before returning, so it stays
responsive regardless of how much background processing is queued up
(requirement: "the API should remain responsive while background processing
occurs").

## Asynchronous Processing & State Transitions

A transaction moves through:

```
RECEIVED  →  PROCESSING  →  SUCCESS
                         ↘  FAILED
```

- **RECEIVED**: created by `POST /transactions`, immediately enqueued.
- **PROCESSING**: set by the worker the instant it picks the transaction off
  the queue.
- **SUCCESS**: the business check passed and the balance was updated.
- **FAILED**: either a business rule failed (insufficient balance) or a
  transient failure exhausted its retries.

Transactions that fail *basic* validation (non-positive amount, invalid
`type`) never reach `RECEIVED`/`PROCESSING` at all — they're recorded as
`FAILED` synchronously in the request handler, because no amount of
background processing could ever make them succeed (see
[ASSUMPTIONS.md](ASSUMPTIONS.md)).

## Concurrency Protection

The requirement: two DEBITs for the same customer arriving nearly
simultaneously must not corrupt the balance, and exactly the ones the balance
can actually support should succeed.

Implementation (`app/service.py::process_transaction`,
`app/queue_worker.py::get_customer_lock`):

1. Each worker thread, before touching a transaction's balance, resolves a
   `threading.Lock` keyed by `customer_id` (created lazily in a dict guarded
   by a small meta-lock, so lock creation itself is race-free).
2. The worker acquires that lock, *then* reloads the customer's row from the
   database (not a value captured earlier), checks
   `balance - amount >= 0` for a DEBIT, applies the update, commits, and only
   then releases the lock.
3. Because the read-check-write sequence for a given customer never happens
   outside that lock, two threads processing two DEBITs for the same
   customer are strictly serialized — the second one always sees the
   balance *after* the first one's write. There is no window where both can
   read the same stale balance and both decide they have enough funds.
4. Different customers use different locks, so unrelated transactions still
   process in parallel across the worker pool.

This is deliberately a simple, single-process synchronization primitive
(rather than e.g. SQLite's own locking or `SELECT ... FOR UPDATE`, which
SQLite doesn't support) — appropriate for the in-memory-queue, single-process
scope of this assignment. See [`test_concurrency.py`](backend/tests/test_concurrency.py)
for two tests that exercise this directly (a 2-way and a 10-way simultaneous
debit race).

## Idempotency

`transaction_id` is the primary key of the `transactions` table. On
`POST /transactions`:

- If a row with that id already exists (in any status — `RECEIVED`,
  `PROCESSING`, `SUCCESS`, or `FAILED`), the existing row is returned as-is.
  Nothing is re-enqueued, nothing is re-applied.
- If two identical requests race each other before either has committed, the
  DB's `PRIMARY KEY` constraint rejects the second `INSERT`; the handler
  catches `IntegrityError` and returns the row the other request just wrote.

This satisfies both "the same `transaction_id` must not be applied more than
once" and "if submitted while already processing, return the existing
status" with a single code path.

## Retries & Failure Handling

`app/service.py::process_transaction` runs an attempt loop (bounded by
`MAX_RETRIES`, default 3) around a single injection point,
`_maybe_simulate_transient_failure(attempt)`. In normal operation this is a
no-op (`TRANSIENT_FAILURE_RATE=0`), so demo behavior is fully deterministic;
tests monkeypatch it to force transient failures on demand.

- A `TransientProcessingError` increments `processing_attempts`, records the
  reason, and — if attempts remain — retries after a short backoff
  (`RETRY_BACKOFF_SECONDS`, default 50ms). Each attempt (including the
  backoff sleep) runs under the customer's lock, so a retrying transaction
  briefly delays other transactions for the *same* customer but never
  affects other customers. If retries are exhausted, the transaction is
  marked `FAILED` with `"Max retry attempts exceeded: ..."`.
- A business-rule failure (insufficient balance) is not a
  `TransientProcessingError` — it returns immediately as `FAILED` with
  `processing_attempts == 1`, never retried.

## Known Limitations & Production Improvements

This was built in hours, not production-hardened. For a production system:

- **Durability of the queue**: the in-memory `queue.Queue` is lost on process
  restart. A `RECEIVED` transaction that hasn't been picked up yet would be
  stuck if the process crashed. Production would use a durable queue (or at
  minimum, a "recover unprocessed RECEIVED rows on startup" reconciliation
  step) — deliberately out of scope here per the assignment's constraint
  against hosted queues.
- **SQLite** is fine for local/dev use but not for multi-process concurrent
  writers; a production deployment would use PostgreSQL with row-level
  locking (`SELECT ... FOR UPDATE`) instead of an in-process
  `threading.Lock`, so the concurrency guarantee holds across multiple API
  server processes too.
- **No authentication/authorization** on any endpoint — out of scope per the
  assignment's speed constraints, but required before any real deployment.
- **No structured logging/metrics/tracing** — only basic Python logging.
- **Currency is stored but not validated or converted** — no FX logic, no
  ISO-4217 validation.
- **Transient-failure simulation is a test hook, not a real fault** — a
  production system would derive "transient" from actual downstream
  exceptions (timeouts, connection errors) rather than an injectable
  function.
- **Worker pool size is fixed** (`NUM_WORKERS=3`) and not adaptive to load.
