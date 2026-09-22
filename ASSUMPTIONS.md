# Assumptions

- **Missing `transaction_id`/`customer_id` vs. bad `amount`/`type` are
  handled differently.** `transaction_id` and `customer_id` are required,
  non-empty strings enforced by the Pydantic request schema — a request
  missing either gets an HTTP `422` (nothing can be stored or shown as a
  "transaction" without an id). A bad `amount` (<= 0) or bad `type` (not
  `CREDIT`/`DEBIT`) is treated as a *business* validation failure per
  Section 4 of the spec: the request is accepted (`201`), a transaction row
  is created with `status: "FAILED"` and a `failure_reason`, so the caller
  gets a normal transaction resource back rather than a generic HTTP error.

- **Unknown `customer_id`s are created lazily** with a balance of 0 on first
  reference, rather than rejected. The spec doesn't define a customer
  registration flow, and this keeps CREDIT-to-fund-a-new-customer working
  naturally while still failing any DEBIT against an unfunded/unknown
  customer with "Insufficient balance".

- **Hard validation failures (bad amount/type) skip the RECEIVED/PROCESSING
  states** and go straight to `FAILED`, since no background processing could
  ever change that outcome. Transactions that depend on current balance
  state (anything that reaches the worker) do go through
  `RECEIVED → PROCESSING → SUCCESS/FAILED` as specified.

- **"Transient processing failure" is simulated, not real**, since there's no
  real external dependency in this local system to fail transiently. The
  retry path is implemented as a first-class code path
  (`TransientProcessingError` + `MAX_RETRIES` loop) with a test-controlled
  injection hook, disabled by default so demo/local behavior is
  deterministic. See [ARCHITECTURE.md](ARCHITECTURE.md#retries--failure-handling).

- **Currency is stored but not validated/converted.** No ISO-4217 checking,
  no FX. Assumed out of scope.

- **Duplicate submission returns `201` with the existing resource**, not a
  `409 Conflict`, since the assignment phrases this as "return the existing
  transaction/status" rather than reject the request.

- **Pagination** uses simple `page`/`page_size` query params (1-indexed),
  not cursor-based, since history size in this local/demo context is small.

- **Single-process deployment assumed.** The concurrency guarantee
  (per-customer `threading.Lock`) only holds within one Python process, which
  matches the assignment's "everything must run locally" / single
  local-queue-and-worker constraint.
