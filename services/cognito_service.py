import time
from typing import Dict
import httpx
import boto3
from fastapi import HTTPException, status, Depends
from config.settings import settings
from jose import jwt, JWTError, jwk
from config.settings import settings
from models.auth import TokenPayload
from fastapi.security import OAuth2PasswordBearer
from models.auth import User

cognito_client = boto3.client('cognito-idp', region_name=settings.AWS_REGION)

# jwks_cache = {}
# jwks_cache_timestamp = 0

class CognitoService:
    
    jwks_cache = {}
    jwks_cache_timestamp = 0

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
    
    @staticmethod      
    async def get_jwks():
        if time.time() - CognitoService.jwks_cache_timestamp > settings.JWKS_CACHE_TIMEOUT:
            async with httpx.AsyncClient() as client:
                response = await client.get(settings.KEYS_URL)
                CognitoService.jwks_cache = response.json()['keys']
            CognitoService.jwks_cache_timestamp = time.time()
        return CognitoService.jwks_cache
    
    @staticmethod
    async def decode_and_validate_token(token: str):
        try:
            headers = jwt.get_unverified_headers(token)
            kid = headers['kid']
            
            jwks = await CognitoService.get_jwks()
            key = next((k for k in jwks if k['kid'] == kid), None)
            if not key:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Key not found")
            
            public_key = jwk.construct(key)
            
            payload = jwt.decode(
                token,
                public_key.to_pem(),
                # algorithms=['RS256'],
                # audience=settings.AWS_COGNITO_CLIENT_ID,
                # issuer=settings.KEYS_URL,
                options={'verify_exp': False, "verify_signature": False}
            )
            return TokenPayload(**payload)
        # except HTTPException as e:
        #     raise e
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    @staticmethod
    async def get_current_user(token_payload: TokenPayload):
        return token_payload.sub
    
    @staticmethod
    async def get_current_user_id(token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))):
        try:
            token_payload = await CognitoService.decode_and_validate_token(token)
            current_user = await CognitoService.get_current_user(token_payload)
            return User(user_id=current_user)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))