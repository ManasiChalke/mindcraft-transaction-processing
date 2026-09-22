import os
import queue
import threading
import logging

from app import service

logger = logging.getLogger("app.queue_worker")

NUM_WORKERS = int(os.environ.get("NUM_WORKERS", 3))

transaction_queue: "queue.Queue[str]" = queue.Queue()

_customer_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

_workers: list[threading.Thread] = []
_shutdown = threading.Event()


def get_customer_lock(customer_id: str) -> threading.Lock:
    with _locks_guard:
        lock = _customer_locks.get(customer_id)
        if lock is None:
            lock = threading.Lock()
            _customer_locks[customer_id] = lock
        return lock


def enqueue(transaction_id: str) -> None:
    transaction_queue.put(transaction_id)


def _worker_loop(worker_name: str) -> None:
    while not _shutdown.is_set():
        try:
            transaction_id = transaction_queue.get(timeout=0.2)
        except queue.Empty:
            continue
        try:
            txn_customer_lock = _resolve_customer_lock_for(transaction_id)
            service.process_transaction(transaction_id, txn_customer_lock)
        except Exception:
            logger.exception("Worker %s failed processing %s", worker_name, transaction_id)
        finally:
            transaction_queue.task_done()


def _resolve_customer_lock_for(transaction_id: str) -> threading.Lock:
    from app.database import SessionLocal
    from app.models import Transaction

    session = SessionLocal()
    try:
        txn = session.get(Transaction, transaction_id)
        customer_id = txn.customer_id if txn else transaction_id
        return get_customer_lock(customer_id)
    finally:
        session.close()


def start_workers() -> None:
    if _workers:
        return
    _shutdown.clear()
    for i in range(NUM_WORKERS):
        t = threading.Thread(target=_worker_loop, args=(f"worker-{i}",), daemon=True)
        t.start()
        _workers.append(t)


def stop_workers() -> None:
    _shutdown.set()
    for t in _workers:
        t.join(timeout=1)
    _workers.clear()


