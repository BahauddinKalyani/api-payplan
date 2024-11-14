from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PAYPLAN_AWS_REGION: str
    PAYPLAN_AWS_COGNITO_USER_POOL_ID: str
    PAYPLAN_AWS_COGNITO_CLIENT_ID: str
    JWKS_CACHE_TIMEOUT: int = 3600
    
    @property
    def KEYS_URL(self):
        return f'https://cognito-idp.{self.AWS_REGION}.amazonaws.com/{self.AWS_COGNITO_USER_POOL_ID}/.well-known/jwks.json'

settings = Settings()

class DBConf(BaseSettings):
    PAYPLAN_AWS_ACCESS_KEY_ID: str
    PAYPLAN_AWS_SECRET_ACCESS_KEY: str
    PAYPLAN_TRANSACTION_TABLE_NAME: str
    
dbconf = DBConf()