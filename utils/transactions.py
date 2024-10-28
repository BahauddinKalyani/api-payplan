from services.transactions_service import TransactionService
from config.settings import settings
from config.settings import dbconf

def get_transaction_service():
    return TransactionService(
        region_name=settings.AWS_REGION,
        aws_access_key_id=dbconf.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=dbconf.AWS_SECRET_ACCESS_KEY,
        table_name=dbconf.Transaction_Table_Name
    )