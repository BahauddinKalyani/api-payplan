from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from models.transactions import IncomeTransaction, ExpenseTransaction, Transaction, TransactionType
from services.transactions_service import TransactionService
from utils.transactions import get_transaction_service

transaction_router = APIRouter()

@transaction_router.post("/income", response_model=Transaction)
async def create_income(transaction: IncomeTransaction, service: TransactionService = Depends(get_transaction_service)):
    return await service.create_transaction(transaction)

@transaction_router.post("/expense", response_model=Transaction)
async def create_expense(transaction: ExpenseTransaction, service: TransactionService = Depends(get_transaction_service)):
    return await service.create_transaction(transaction)

@transaction_router.get("/{transaction_id}", response_model=Transaction)
async def get_transaction(transaction_id: str, service: TransactionService = Depends(get_transaction_service)):
    return await service.get_transaction(transaction_id)

@transaction_router.put("/{transaction_id}", response_model=Transaction)
async def update_transaction(transaction_id: str, transaction: Transaction, service: TransactionService = Depends(get_transaction_service)):
    return await service.update_transaction(transaction_id, transaction)

@transaction_router.delete("/{transaction_id}", response_model=dict)
async def delete_transaction(transaction_id: str, service: TransactionService = Depends(get_transaction_service)):
    return await service.delete_transaction(transaction_id)

# @transaction_router.get("/all", response_model=List[Transaction])
# async def list_transactions(type: Optional[TransactionType] = None, service: TransactionService = Depends(get_transaction_service)):
#     return await service.list_transactions(type)

@transaction_router.get("/user/{user_id}", response_model=List[Transaction])
async def get_user_transactions(user_id: str, service: TransactionService = Depends(get_transaction_service)):
    return await service.get_transactions_by_user_id(user_id)