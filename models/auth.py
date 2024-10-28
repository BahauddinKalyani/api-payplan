from pydantic import BaseModel

class SignUpModel(BaseModel):
    first_name: str
    middle_name: str
    last_name: str
    username: str
    email: str
    password: str

class ConfirmSignUpModel(BaseModel):
    username: str
    confirmation_code: str

class TokenPayload(BaseModel):
    sub: str

class User(BaseModel):
    user_id: str