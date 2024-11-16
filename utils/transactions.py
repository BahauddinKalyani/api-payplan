from services.transaction_service import TransactionService
from config.settings import settings
from config.settings import dbconf
import requests

def get_transaction_service():
    return TransactionService(
        region_name=settings.AWS_REGION,
        aws_access_key_id=dbconf.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=dbconf.AWS_SECRET_ACCESS_KEY,
        table_name=dbconf.TRANSACTION_TABLE_NAME
    )
    
def get_jwks(user_pool_id):
    region = user_pool_id.split('_')[0]  # Extract region from user pool ID
    jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
    
    
    response = requests.get(jwks_url)
    return response.json(), jwks_url