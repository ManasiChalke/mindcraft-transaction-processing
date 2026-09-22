# AI Usage Disclosure

The assignment explicitly requires disclosure — including chat
screenshots/exports — when AI is used. This project was built with substantial
AI assistance.

## Tool used

Claude Code (Anthropic), an AI coding agent, running in a terminal/VSCode
environment against this repository (`D:\Task`).

## What the AI did

- Read the assignment PDF and derived requirements from it.
- Designed and wrote the FastAPI backend: models, schemas, business/validation
  logic, the in-memory queue + threaded worker pool, concurrency locking, and
  retry logic.
- Wrote the React (Vite) frontend: API service layer, transaction form,
  balance card, transaction history/pagination.
- Wrote the backend pytest suite (15 tests) and frontend vitest suite
  (4 tests), ran them, and fixed failures until all passed.
- Ran the application end-to-end (both servers) and manually verified every
  API flow (CREDIT, DEBIT, insufficient balance, duplicate submission,
  history, pagination) with live `curl` requests.
- Wrote this documentation set (README, ARCHITECTURE, ASSUMPTIONS, TESTING,
  this file, the requirements checklist).

## What I (the candidate) should do before submitting

1. **Preserve the chat transcript/screenshots** of this AI session as
   evidence, per the assignment's requirement. Concretely:
   - Export or screenshot the conversation in your Claude Code client
     (the sidebar/history typically has an export option), or take
     screenshots of the key exchanges (the initial request and the final
     summary at minimum).
   - Save them alongside the submission, e.g. in an `ai_chat_evidence/`
     folder, named clearly (e.g. `ai_chat_01.png`, `ai_chat_02.png`).
2. **Personally review every file** — don't submit code you can't explain.
   Read through `backend/app/service.py` (business logic + concurrency +
   retry) and `backend/app/queue_worker.py` (queue/worker pool) in
   particular, since those are the parts most likely to come up in a
   follow-up conversation.
3. **Run the app and tests yourself** (commands are in the README) so you can
   speak to actual, first-hand behavior, not just what this document claims.
4. **Fill in [TIME_LOG.md](TIME_LOG.md)** with your own honest time spent
   reviewing/verifying, not the AI's generation time.
5. If asked in an interview to modify or extend the code live, be prepared to
   navigate `backend/app/` and `frontend/src/` without AI assistance.
