from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    AWS_REGION: str
    AWS_COGNITO_USER_POOL_ID: str
    AWS_COGNITO_CLIENT_ID: str
    JWKS_CACHE_TIMEOUT: int = 3600
    ALLOWED_ORIGINS: str
    
    @property
    def KEYS_URL(self):
        return f'https://cognito-idp.{self.AWS_REGION}.amazonaws.com/{self.AWS_COGNITO_USER_POOL_ID}/.well-known/jwks.json'

settings = Settings()

class DBConf(BaseSettings):
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    TRANSACTION_TABLE_NAME: str
    
dbconf = DBConf()