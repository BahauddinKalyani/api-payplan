from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    AWS_REGION: str
    AWS_COGNITO_USER_POOL_ID: str
    AWS_COGNITO_CLIENT_ID: str

settings = Settings()