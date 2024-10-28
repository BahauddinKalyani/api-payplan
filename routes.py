from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from models.auth import SignUpModel, ConfirmSignUpModel
from services.cognito_service import CognitoService

router = APIRouter()

@router.post("/signup")
async def signup(user: SignUpModel):
    return await CognitoService.sign_up(user)

@router.post("/confirm-signup")
async def confirm_signup(confirm: ConfirmSignUpModel):
    return await CognitoService.confirm_sign_up(confirm)

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return await CognitoService.login(form_data.username, form_data.password)

@router.post("/logout")
async def logout(token: str):
    return await CognitoService.logout(token)