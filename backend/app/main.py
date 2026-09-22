from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, SessionLocal
from app.models import Customer, Transaction
from app.schemas import (
    TransactionCreate,
    TransactionOut,
    BalanceOut,
    TransactionHistoryOut,
    HealthOut,
)
from app import service
from app.queue_worker import enqueue, start_workers, stop_workers, transaction_queue

SEED_CUSTOMERS = {
    "CUST001": 10000.0,
    "CUST002": 5000.0,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    session = SessionLocal()
    try:
        for customer_id, balance in SEED_CUSTOMERS.items():
            if session.get(Customer, customer_id) is None:
                session.add(Customer(customer_id=customer_id, balance=balance, currency="INR"))
        session.commit()
    finally:
        session.close()
    start_workers()
    yield
    stop_workers()


app = FastAPI(title="Transaction Processing API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthOut)
def health():
    return HealthOut(status="ok", queue_size=transaction_queue.qsize())


@app.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(payload: TransactionCreate):
    txn, was_enqueued = service.submit_transaction(payload)
    if was_enqueued:
        enqueue(txn.transaction_id)
    return txn


@app.get("/transactions/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: str):
    session = SessionLocal()
    try:
        txn = session.get(Transaction, transaction_id)
        if txn is None:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return txn
    finally:
        session.close()


@app.get("/customers/{customer_id}/balance", response_model=BalanceOut)
def get_balance(customer_id: str):
    session = SessionLocal()
    try:
        customer = session.get(Customer, customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer
    finally:
        session.close()


@app.get("/customers/{customer_id}/transactions", response_model=TransactionHistoryOut)
def get_customer_transactions(
    customer_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    session = SessionLocal()
    try:
        query = (
            session.query(Transaction)
            .filter(Transaction.customer_id == customer_id)
            .order_by(Transaction.created_at.desc())
        )
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return TransactionHistoryOut(items=items, total=total, page=page, page_size=page_size)
    finally:
        session.close()
