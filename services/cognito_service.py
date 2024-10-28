import boto3
from fastapi import HTTPException
from config.settings import settings

cognito_client = boto3.client('cognito-idp', region_name=settings.AWS_REGION)

class CognitoService:
    @staticmethod
    async def sign_up(user):
        try:
            response = cognito_client.sign_up(
                ClientId=settings.AWS_COGNITO_CLIENT_ID,
                Username=user.username,
                Password=user.password,
                UserAttributes=[
                    {'Name': 'email', 'Value': user.email},
                ]
            )
            return {"message": "User signed up successfully", "userSub": response['UserSub']}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    async def confirm_sign_up(confirm):
        try:
            cognito_client.confirm_sign_up(
                ClientId=settings.AWS_COGNITO_CLIENT_ID,
                Username=confirm.username,
                ConfirmationCode=confirm.confirmation_code
            )
            return {"message": "User confirmed successfully"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    async def login(username, password):
        try:
            response = cognito_client.initiate_auth(
                ClientId=settings.AWS_COGNITO_CLIENT_ID,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            return {
                "access_token": response['AuthenticationResult']['AccessToken'],
                "token_type": "bearer"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    async def logout(token):
        try:
            cognito_client.global_sign_out(AccessToken=token)
            return {"message": "User logged out successfully"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))