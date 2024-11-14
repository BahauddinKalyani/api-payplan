from pydantic import BaseModel
from typing import Optional

class SignUpModel(BaseModel):
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    username: str
    email: str
    password: str
    balance: Optional[int] = None

class ConfirmSignUpModel(BaseModel):
    username: str
    confirmation_code: str

class TokenPayload(BaseModel):
    sub: str

class User(BaseModel):
    user_id: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    username: str
    email: str
    password: str
    balance: Optional[int] = None