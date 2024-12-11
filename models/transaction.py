from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from decimal import Decimal

class TransactionType(str, Enum):
    income = "income"
    expense = "expense"

class TransactionFrequency(str, Enum):
    one_time = "one-time"
    weekly = "weekly"
    bi_weekly = "bi-weekly"
    semi_monthly = "semi-monthly"
    monthly = "monthly"

class TransactionBase(BaseModel):
    user_id: str
    type: TransactionType
    name: str
    amount: Decimal = Field(..., ge=0)
    frequency: TransactionFrequency
    date_of_transaction: Optional[str] = None
    date_of_second_transaction: Optional[str] = None
    day: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    skip_end_date: Optional[bool] = False
    last_day_of_month: Optional[bool] = False

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: str

    # class Config:
    #     orm_mode = True