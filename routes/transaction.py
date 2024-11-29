"""Transaction routes"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import APIKeyCookie
from models.transaction import Transaction, TransactionCreate
from utils.transactions import get_transaction_service
from services.cognito_service import CognitoService
from services.main_service import MainService

transaction_service = get_transaction_service()

SECRET_KEY = "your_secret_key"  # Replace with your actual secret key
ALGORITHM = "HS256"

cookie_scheme = APIKeyCookie(name="access_token")

# Dependency to verify the token
async def verify_token(token: str = Depends(cookie_scheme)):
    """Verify the token and return the payload"""
    if not token:
        raise HTTPException(status_code=403, detail="Not authenticated")
    try:
        # Decode the JWT token
        payload = CognitoService.get_current_user_id(token)
        # Optionally check for expiration
        if not payload:
            raise HTTPException(status_code=401, detail="Token has expired")
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e

t_router = APIRouter(
    dependencies=[Depends(verify_token)],
)
@t_router.post("/transactions", response_model=Transaction)
async def create_transaction(transaction: TransactionCreate):
    """Create a new transaction"""
    return transaction_service.create_transaction(transaction)

@t_router.get("/transactions/{transaction_id}", response_model=Transaction)
async def read_transaction(transaction_id: str):
    """Get a transaction by ID"""
    transaction = transaction_service.get_transaction(transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@t_router.put("/transactions/{transaction_id}", response_model=Transaction)
async def update_transaction(
        transaction_id: str,
        transaction: TransactionCreate
    ):
    """Update a transaction"""
    updated_transaction = transaction_service.update_transaction(transaction_id, transaction)
    if updated_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return updated_transaction

@t_router.delete("/transactions/{transaction_id}", response_model=dict)
async def delete_transaction(transaction_id: str):
    """Delete a transaction"""
    transaction_service.delete_transaction(transaction_id)
    return {"message": "Transaction deleted successfully"}

@t_router.get("/users/{user_id}/transactions", response_model=list[Transaction])
async def get_user_transactions(user_id: str):
    """Get all transactions for a user"""
    return transaction_service.list_user_transactions(user_id)

@t_router.get("/users/{user_id}/balance")
def get_user_balance(user_id: str):
    """Get the balance for a user"""
    service=MainService(user_id)
    return service.calculate_balances()
