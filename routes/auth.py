"""Routes for authentication"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm, APIKeyCookie
from models.auth import SignUpModel, ConfirmSignUpModel
from services.cognito_service import CognitoService

cookie_scheme = APIKeyCookie(name="access_token")

async def verify_token(token: str = Depends(cookie_scheme)):
    """Verify the token and return the payload"""
    if not token:
        raise HTTPException(status_code=403, detail="Not authenticated")
    try:
        payload = CognitoService.get_current_user_id(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Token has expired")
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e

auth_router = APIRouter()

@auth_router.post("/signup")
async def signup(user: SignUpModel):
    """Sign up a new user"""
    return await CognitoService.sign_up(user)

@auth_router.post("/confirm-signup")
async def confirm_signup(confirm: ConfirmSignUpModel):
    """Confirm the sign up"""
    return await CognitoService.confirm_sign_up(confirm)

@auth_router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login the user"""
    return await CognitoService.login(form_data.username, form_data.password)

@auth_router.get("/check-auth")
async def check_auth(current_user: dict = Depends(verify_token)):
    """Check if the user is authenticated"""
    return {"authenticated": True, "user": current_user}

@auth_router.post("/logout")
async def logout(token: str = Depends(cookie_scheme)):
    """Logout the user"""
    return await CognitoService.logout(token)

@auth_router.get("/users/me")
async def read_users_me(token: str):
    """Get the current user"""
    return await CognitoService.get_current_user_id(token)

# @auth_router.post("/refresh-token")
# async def refresh_token(token: str):
#     return await CognitoService.refresh_token(token)

@auth_router.post("/forgot-password")
async def forgot_password(username: str):
    """Forgot password"""
    return await CognitoService.forgot_password(username)

@auth_router.post("/confirm-forgot-password")
async def confirm_forgot_password(username: str, code: str, new_password: str):
    """Confirm forgot password"""
    return await CognitoService.confirm_forgot_password(username, code, new_password)

@auth_router.post("/change-password")
async def change_password(token: str, old_password: str, new_password: str):
    """Change password"""
    return await CognitoService.change_password(token, old_password, new_password)

