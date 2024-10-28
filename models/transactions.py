from pydantic import BaseModel
from enum import Enum
from typing import Optional
from datetime import date

class Frequency(str, Enum):
    ONE_TIME = "one-time"
    WEEKLY = "weekly"
    BI_WEEKLY = "bi-weekly"
    MONTHLY = "monthly"

class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"

class Transaction(BaseModel):
    id: str
    user_id: str
    type: TransactionType
    name: str
    amount: int
    frequency: Frequency
    start_date: str
    end_date: Optional[str] = None
    due_date: Optional[str] = None
    auto_deduct: Optional[bool] = None

class IncomeTransaction(Transaction):
    type: TransactionType = TransactionType.INCOME

class ExpenseTransaction(Transaction):
    type: TransactionType = TransactionType.EXPENSE
    due_date: date
    auto_deduct: bool