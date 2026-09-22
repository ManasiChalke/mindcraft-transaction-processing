from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    transaction_id: str = Field(..., min_length=1)
    customer_id: str = Field(..., min_length=1)
    amount: float
    currency: str = "INR"
    type: str


class TransactionOut(BaseModel):
    transaction_id: str
    customer_id: str
    amount: float
    currency: str
    type: str
    status: str
    failure_reason: Optional[str] = None
    processing_attempts: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BalanceOut(BaseModel):
    customer_id: str
    balance: float
    currency: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionHistoryOut(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int


class HealthOut(BaseModel):
    status: str
    queue_size: int
