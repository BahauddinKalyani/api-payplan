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
from botocore.exceptions import ClientError

from utils.transactions import get_jwks

from jose import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cognito_client = boto3.client('cognito-idp', region_name=settings.AWS_REGION)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# jwks_cache = {}
# jwks_cache_timestamp = 0

class CognitoService:
    
    jwks_cache = {}
    jwks_cache_timestamp = 0

    @staticmethod
    def email_exists(email):
        try:
            response = cognito_client.list_users(
                UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                Filter=f'email = "{email}"'
            )
            return len(response['Users']) > 0
        except ClientError as e:
            logger.error(f"Error checking email existence: {e}")
            raise HTTPException(status_code=500, detail="Error checking email existence")
    
    @staticmethod
    async def sign_up(user):
        
        if CognitoService.email_exists(user.email):
            raise HTTPException(status_code=409, detail="Email already exists.")
        try:
            response = cognito_client.sign_up(
                ClientId=settings.AWS_COGNITO_CLIENT_ID,
                Username=user.username,
                Password=user.password,
                UserAttributes=[
                    {'Name': 'email', 'Value': user.email},
                    {'Name': 'given_name', 'Value': ' '},
                    {'Name': 'family_name', 'Value': ' '},
                    {'Name': 'custom:balance', 'Value': '0'}
                ]
            )
            return {"message": "User signed up successfully", "userSub": response['UserSub']}
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                raise HTTPException(status_code=409, detail="User already exists.")
            elif error_code == 'InvalidPasswordException':
                raise HTTPException(status_code=400, detail="Invalid password format.")
            elif error_code == 'InvalidParameterException':
                raise HTTPException(status_code=400, detail="Invalid parameters provided.")
            else:
                raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # For any other unexpected exceptions
            logger.error(f"Error: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

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
            logger.error(f"Error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    @staticmethod
    def parse_user_attributes(user_data):
        parsed_data = {
            "username": user_data["Username"],
        }
        for attribute in user_data["UserAttributes"]:
            parsed_data[attribute["Name"]] = attribute["Value"]

        return parsed_data

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
            user_info = cognito_client.get_user(
                AccessToken=response['AuthenticationResult']['AccessToken']
            )
            
            parsed_data = CognitoService.parse_user_attributes(user_info)
            # return parsed_data
            tokens =  {
                "access_token": response['AuthenticationResult']['AccessToken'],
                "refresh_token": response['AuthenticationResult']['RefreshToken'],
                "id_token": response['AuthenticationResult']['IdToken'],
                "expires_in": response['AuthenticationResult']['ExpiresIn'],
            }
            tokens.update(parsed_data)
            return tokens
            
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
    
    # @staticmethod
    # async def get_current_user(token_payload: TokenPayload):
    #     user_info = cognito_client.get_user(
    #         AccessToken=current_user.access_token
    #     )
    #     return token_payload.sub
    
    # @staticmethod
    # async def get_current_user_id(token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))):
    #     try:
    #         token_payload = await CognitoService.decode_and_validate_token(token)
    #         current_user = await CognitoService.get_current_user(token_payload)
    #         return User(user_id=current_user)
    #     except HTTPException as e:
    #         raise e
    #     except Exception as e:
    #         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
    # @staticmethod    
    # async def get_current_user(token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))):
    #     credentials_exception = HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Could not validate credentials",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    #     try:
    #         # Verify the token with Cognito
    #         # logger.info(f"Token: {token}")
    #         response = cognito_client.get_user(
    #             AccessToken=token
    #         )
    #         username = response['Username']
    #         return username
    #     except Exception as e:
    #         logger.error(f"Error: {e}")
    #         raise credentials_exception
        
    # def get_current_user_id(token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))):
    #     credentials_exception = HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Could not validate credentials",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    #     try:
    #         # Verify the token with Cognito
    #         response = cognito_client.get_user(
    #             AccessToken=token
    #         )
    #         username = response['sub']
    #         return username
    #     except Exception:
    #         raise credentials_exception
    
    @staticmethod
    async def get_current_user(token: str = Depends(oauth2_scheme)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            # Decode the token (without verification) to get the 'sub' claim
            payload = jwt.get_unverified_claims(token)
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        try:
            # Verify the token with Cognito
            response = cognito_client.get_user(AccessToken=token)
            if response['Username'] != username:
                raise credentials_exception
            
            # You can return more user information here if needed
            return {
                "username": username,
                "email": next((attr['Value'] for attr in response['UserAttributes'] if attr['Name'] == 'email'), None)
            }
        except cognito_client.exceptions.NotAuthorizedException:
            raise credentials_exception
        except Exception as e:
            logger.error(f"Error: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
        
    @staticmethod
    async def get_current_user_id(token: str = Depends(oauth2_scheme)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            # Decode the token (without verification) to get the 'sub' claim
            payload = jwt.get_unverified_claims(token)
            username: str = payload.get("sub")
            return username
            # if username is None:
            #     raise credentials_exception
        except JWTError:
            raise credentials_exception

        # try:
        #     # Verify the token with Cognito
        #     response = cognito_client.get_user(AccessToken=token)
        #     if response['Username'] != username:
        #         raise credentials_exception
            
        #     # You can return more user information here if needed
        #     return response['sub']
        # except cognito_client.exceptions.NotAuthorizedException:
        #     raise credentials_exception
        # except Exception as e:
        #     logger.error(f"Error: {e}")
        #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")