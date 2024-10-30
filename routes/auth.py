from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from models.auth import SignUpModel, ConfirmSignUpModel
from services.cognito_service import CognitoService

from typing import List, Optional
from models.transactions import IncomeTransaction, ExpenseTransaction, Transaction, TransactionType
from services.transactions_service import TransactionService
from utils.transactions import get_transaction_service

auth_router = APIRouter()

@auth_router.post("/signup")
async def signup(user: SignUpModel):
    return await CognitoService.sign_up(user)

@auth_router.post("/confirm-signup")
async def confirm_signup(confirm: ConfirmSignUpModel):
    return await CognitoService.confirm_sign_up(confirm)

@auth_router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return await CognitoService.login(form_data.username, form_data.password)

@auth_router.post("/logout")
async def logout(token: str):
    return await CognitoService.logout(token)

@auth_router.get("/users/me")
async def read_users_me(token: str):
    return await CognitoService.get_current_user_id(token)