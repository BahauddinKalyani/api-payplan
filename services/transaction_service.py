"""Service class to interact with the DynamoDB table"""
import uuid
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from models.transaction import Transaction, TransactionCreate

class TransactionService:
    """Service class to interact with the DynamoDB table"""
    def __init__(self, region_name, aws_access_key_id, aws_secret_access_key, table_name):
        self.dynamodb  = boto3.resource('dynamodb',
                                     region_name=region_name,
                                     aws_access_key_id=aws_access_key_id,
                                     aws_secret_access_key=aws_secret_access_key)
        self.table = self.dynamodb.Table(table_name)

    def create_transaction(self, transaction: TransactionCreate) -> Transaction:
        """Create a new transaction"""
        transaction_dict = transaction.dict()
        transaction_dict['id'] = str(uuid.uuid4())
        # transaction_dict['user_id'] = user_id
        transaction_dict['amount'] = Decimal(str(transaction_dict['amount']))
        try:
            self.table.put_item(Item=transaction_dict)
            return Transaction(**transaction_dict)
        except ClientError as e:
            print(e.response['Error']['Message'])
            raise

    def get_transaction(self, transaction_id: str) -> Transaction:
        """Get a transaction by ID"""
        try:
            # response = self.table.get_item(Key={'id': transaction_id, 'user_id': user_id})
            response = self.table.get_item(Key={'id': transaction_id})
            item = response.get('Item')
            if item:
                return Transaction(**item)
            else:
                return None
        except ClientError as e:
            print(e.response['Error']['Message'])
            raise

    def update_transaction(
        self,
        transaction_id: str,
        transaction: TransactionCreate
        ) -> Transaction:
        """Update a transaction"""
        try:
            update_expression = "SET "
            expression_attribute_values = {}
            expression_attribute_names = {}
            for key, value in transaction.model_dump(exclude_unset=True).items():
                if key not in ['id', 'user_id']:
                    if key == 'amount':
                        value = Decimal(str(value))
                    placeholder = f":val_{key}"
                    name_placeholder = f"#name_{key}"
                    update_expression += f"{name_placeholder} = {placeholder}, "
                    expression_attribute_values[placeholder] = value
                    expression_attribute_names[name_placeholder] = key

            # Remove trailing comma and space
            update_expression = update_expression.rstrip(', ')
            if not expression_attribute_values:
                # return existing_transaction  # No fields to update
                return transaction.model_dump()

            # Perform the update
            response = self.table.update_item(
                Key={'id': transaction_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
                ReturnValues="ALL_NEW"
            )

            return Transaction(**response['Attributes'])
        except ClientError as e:
            print(e.response['Error']['Message'])
            raise

    def delete_transaction(self, transaction_id: str):
        """Delete a transaction"""
        try:
            self.table.delete_item(Key={'id': transaction_id})
        except ClientError as e:
            print(e.response['Error']['Message'])
            raise

    def list_user_transactions(self, user_id: str):
        """Get all transactions for a user"""
        try:
            response = self.table.query(
                IndexName='user_id_index',
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id}
            )
            return [Transaction(**item) for item in response['Items']]
        except ClientError as e:
            print(e.response['Error']['Message'])
            raise

    def borrow_money(self, user_id: str, attributes: dict):
        """Borrow money"""
        try:

            transaction_income = TransactionCreate(
                user_id = user_id,
                name = 'Borrowed Money',
                amount = Decimal(str(attributes['amount_borrowed'])),
                type = 'income',
                frequency = 'one-time',
                start_date=None,
                end_date=None,
                date_of_transaction = attributes['current_date']
            )
            transaction_income = self.create_transaction(transaction_income)
            transaction_expense = TransactionCreate(
                user_id = user_id,
                name='Return Borrowed Money',
                amount=Decimal(str(attributes['amount_to_be_returned'])),
                type='expense',
                frequency='one-time',
                start_date=None,
                end_date=None,
                date_of_transaction = attributes['date_of_return']
            )
            transaction_expense = self.create_transaction(transaction_expense)
            return [transaction_income, transaction_expense]
        except ClientError as e:
            print(e.response['Error']['Message'])
            raise
