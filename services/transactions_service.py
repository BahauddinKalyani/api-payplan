import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException
from models.transactions import Transaction
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
            response = self.table.get_item(Key={'user_id': transaction_id})
            item = response.get('Item')
            if not item:
                raise HTTPException(status_code=404, detail="Transaction not found")
            return item
        except ClientError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def update_transaction(self, transaction_id: str, transaction: Transaction):
        try:
            update_expression = "set "
            expression_attribute_values = {}
            for key, value in transaction.model_dump(exclude_unset=True).items():
                if key != 'id' and key != 'user_id':  # Don't update id or user_id
                    update_expression += f" {key} = :{key},"
                    expression_attribute_values[f":{key}"] = value
            update_expression = update_expression.rstrip(',')

            response = self.table.update_item(
                Key={'id': transaction_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="ALL_NEW"
            )
            return response['Attributes']
        except ClientError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_transaction(self, transaction_id: str):
        try:
            response = self.table.delete_item(Key={'id': transaction_id})
            return {"message": "Transaction deleted successfully"}
        except ClientError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def list_transactions(self, transaction_type: str = None):
        try:
            if transaction_type:
                response = self.table.scan(
                    FilterExpression=boto3.dynamodb.conditions.Attr('type').eq(transaction_type)
                )
            else:
                response = self.table.scan()
            return response['Items']
        except ClientError as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_transactions_by_user_id(self, user_id: str):
        try:
            response = self.table.query(
                IndexName='UserIdIndex',  # You'll need to create this GSI
                KeyConditionExpression=Key('user_id').eq(user_id)
            )
            return response['Items']
        except ClientError as e:
            raise HTTPException(status_code=500, detail=str(e))