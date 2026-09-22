import os
import time
import random
import logging
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import Customer, Transaction
from app.schemas import TransactionCreate

logger = logging.getLogger("app.service")

VALID_TYPES = {"CREDIT", "DEBIT"}
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", 3))
RETRY_BACKOFF_SECONDS = float(os.environ.get("RETRY_BACKOFF_SECONDS", 0.05))

TRANSIENT_FAILURE_RATE = float(os.environ.get("TRANSIENT_FAILURE_RATE", 0.0))


class TransientProcessingError(Exception):
    pass


def _maybe_simulate_transient_failure(attempt: int) -> None:
    if TRANSIENT_FAILURE_RATE > 0 and random.random() < TRANSIENT_FAILURE_RATE:
        raise TransientProcessingError("Simulated transient processing error")


def get_or_create_customer(session, customer_id: str, currency: str = "INR") -> Customer:
    customer = session.get(Customer, customer_id)
    if customer is None:
        customer = Customer(customer_id=customer_id, balance=0.0, currency=currency)
        session.add(customer)
        session.flush()
    return customer


def _validate_basic(payload: TransactionCreate):
    if payload.amount <= 0:
        return "Amount must be greater than zero"
    if payload.type not in VALID_TYPES:
        return f"Transaction type must be one of {sorted(VALID_TYPES)}"
    return None


def submit_transaction(payload: TransactionCreate) -> tuple[Transaction, bool]:
    session = SessionLocal()
    try:
        existing = session.get(Transaction, payload.transaction_id)
        if existing is not None:
            return existing, False

        failure_reason = _validate_basic(payload)
        status = "FAILED" if failure_reason else "RECEIVED"

        get_or_create_customer(session, payload.customer_id, payload.currency)

        txn = Transaction(
            transaction_id=payload.transaction_id,
            customer_id=payload.customer_id,
            amount=payload.amount,
            currency=payload.currency,
            type=payload.type,
            status=status,
            failure_reason=failure_reason,
            processing_attempts=1 if failure_reason else 0,
        )
        session.add(txn)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.get(Transaction, payload.transaction_id)
            return existing, False

        session.refresh(txn)
        return txn, (status == "RECEIVED")
    finally:
        session.close()


def process_transaction(transaction_id: str, customer_lock) -> None:
    session = SessionLocal()
    try:
        txn = session.get(Transaction, transaction_id)
        if txn is None or txn.status != "RECEIVED":
            return

        txn.status = "PROCESSING"
        session.commit()

        attempt = 0
        while True:
            attempt += 1
            with customer_lock:
                session.refresh(txn)
                customer = session.get(Customer, txn.customer_id)
                try:
                    _maybe_simulate_transient_failure(attempt)

                    if txn.type == "DEBIT" and customer.balance - txn.amount < 0:
                        txn.status = "FAILED"
                        txn.failure_reason = "Insufficient balance"
                        txn.processing_attempts = attempt
                        session.commit()
                        return

                    if txn.type == "CREDIT":
                        customer.balance += txn.amount
                    else:
                        customer.balance -= txn.amount

                    txn.status = "SUCCESS"
                    txn.failure_reason = None
                    txn.processing_attempts = attempt
                    session.commit()
                    return

                except TransientProcessingError as exc:
                    session.rollback()
                    txn = session.get(Transaction, transaction_id)
                    txn.processing_attempts = attempt
                    txn.failure_reason = str(exc)
                    if attempt >= MAX_RETRIES:
                        txn.status = "FAILED"
                        txn.failure_reason = f"Max retry attempts exceeded: {exc}"
                        session.commit()
                        return
                    session.commit()
                    time.sleep(RETRY_BACKOFF_SECONDS)
    except Exception:
        logger.exception("Unexpected error processing transaction %s", transaction_id)
        session.rollback()
        txn = session.get(Transaction, transaction_id)
        if txn is not None:
            txn.status = "FAILED"
            txn.failure_reason = "Unexpected internal error"
            txn.processing_attempts = max(txn.processing_attempts, 1)
            session.commit()
    finally:
        session.close()
