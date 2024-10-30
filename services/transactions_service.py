import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException
from models.transactions import Transaction, TransactionType, IncomeTransaction, ExpenseTransaction
from uuid import uuid4
from boto3.dynamodb.conditions import Key

class TransactionService:
    def __init__(self, region_name, aws_access_key_id, aws_secret_access_key, table_name):
        self.client = boto3.resource('dynamodb',
                                     region_name=region_name,
                                     aws_access_key_id=aws_access_key_id,
                                     aws_secret_access_key=aws_secret_access_key)
        self.table = self.client.Table(table_name)

    async def create_transaction(self, transaction: Transaction):
        try:
            transaction_dict = transaction.model_dump()
            transaction_dict['id'] = str(uuid4())  # Generate a unique ID
            response = self.table.put_item(Item=transaction_dict)
            return transaction_dict
        except ClientError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_transaction(self, transaction_id: str):
        try:
            response = self.table.get_item(Key={'id': transaction_id})
            item = response.get('Item')
            if not item:
                raise HTTPException(status_code=404, detail="Transaction not found")
            return item
        except ClientError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def update_transaction(self, transaction_id: str, transaction: Transaction):
        try:
            update_expression = "SET "
            expression_attribute_values = {}
            expression_attribute_names = {}
            
            for key, value in transaction.model_dump(exclude_unset=True).items():
                if key not in ['id', 'user_id', 'type']:  # Don't update id, user_id, or type
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
            
            updated_transaction = response['Attributes']
            
            # Validate the updated transaction based on its type
            if updated_transaction['type'] == TransactionType.INCOME:
                IncomeTransaction(**updated_transaction)
            elif updated_transaction['type'] == TransactionType.EXPENSE:
                ExpenseTransaction(**updated_transaction)
            else:
                raise ValueError(f"Invalid transaction type: {updated_transaction['type']}")
            
            return updated_transaction
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise HTTPException(status_code=404, detail="Transaction not found")
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_transaction(self, transaction_id: str):
        try:
            response = self.table.delete_item(Key={'id': transaction_id})
            return {"message": "Transaction deleted successfully"}
        except ClientError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_transactions_by_user_id(self, user_id: str):
        try:
            response = self.table.query(
                IndexName='user_id_index',  # You'll need to create this GSI
                KeyConditionExpression=Key('user_id').eq(user_id)
            )
            return response['Items']
        except ClientError as e:
            raise HTTPException(status_code=500, detail=str(e))