from fastapi import APIRouter, HTTPException, Depends
from models.transaction import Transaction, TransactionCreate
from utils.transactions import get_transaction_service
from services.cognito_service import CognitoService
from services.main_service import MainService

t_router = APIRouter(
    # dependencies=[Depends(CognitoService.get_current_user)],
)
transaction_service = get_transaction_service()

@t_router.post("/transactions/", response_model=Transaction)
async def create_transaction(transaction: TransactionCreate, user_id: str = Depends(CognitoService.get_current_user_id)):
    return transaction_service.create_transaction(transaction, user_id)

@t_router.get("/transactions/{transaction_id}", response_model=Transaction)
async def read_transaction(transaction_id: str):
    transaction = transaction_service.get_transaction(transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@t_router.put("/transactions/{transaction_id}", response_model=Transaction)
async def update_transaction(transaction_id: str, transaction: TransactionCreate):
    updated_transaction = transaction_service.update_transaction(transaction_id, transaction)
    if updated_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return updated_transaction

@t_router.delete("/transactions/{transaction_id}", response_model=dict)
async def delete_transaction(transaction_id: str):
    transaction_service.delete_transaction(transaction_id)
    return {"message": "Transaction deleted successfully"}

@t_router.get("/users/{user_id}/transactions", response_model=list[Transaction])
async def get_user_transactions(user_id: str):
    return transaction_service.list_user_transactions(user_id)

@t_router.get("/users/{user_id}/balance")
def get_user_balance(user_id: str):
     service=MainService(user_id)
     return service.calculate_balances()