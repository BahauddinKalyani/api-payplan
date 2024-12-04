"""CognitoService class which provides methods to interact with AWS Cognito."""
import logging
import time
import httpx
import boto3
from botocore.exceptions import ClientError
from jose import jwt, JWTError, jwk
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from models.auth import TokenPayload
from config.settings import settings
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cognito_client = boto3.client('cognito-idp', region_name=settings.AWS_REGION)
boto3.set_stream_logger('botocore', level='DEBUG')

class CognitoService:
    """Service class to interact with AWS Cognito."""
    jwks_cache = {}
    jwks_cache_timestamp = 0

    @staticmethod
    def email_exists(email):
        """Check if an email exists in the Cognito user pool"""
        try:
            response = cognito_client.list_users(
                UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                Filter=f'email = "{email}"'
            )
            return len(response['Users']) > 0
        except ClientError as e:
            logger.error("Error checking email existence: %s", e)
            raise HTTPException(status_code=500, detail="Error checking email existence") from e

    @staticmethod
    async def sign_up(user):
        """Signup a user with Cognito"""
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
                    {'Name': 'custom:balance', 'Value': '0'},
                    {'Name': 'custom:acceptTnC', 'Value': str(user.privacy_policy)}
                ]
            )
            return {"message": "User signed up successfully"}
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                raise HTTPException(status_code=409, detail="User already exists.") from e
            elif error_code == 'InvalidPasswordException':
                raise HTTPException(status_code=400, detail="Invalid password format.") from e
            elif error_code == 'InvalidParameterException':
                raise HTTPException(status_code=400, detail="Invalid parameters provided.") from e
            else:
                raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            # For any other unexpected exceptions
            logger.error("Error: %s", e)
            raise HTTPException(status_code=500, detail="An unexpected error occurred") from e

    @staticmethod
    async def confirm_sign_up(confirm):
        """Confirm the user signup with the confirmation code"""
        try:
            cognito_client.confirm_sign_up(
                ClientId=settings.AWS_COGNITO_CLIENT_ID,
                Username=confirm.username,
                ConfirmationCode=confirm.confirmation_code
            )
            return {"message": "User confirmed successfully"}
        except Exception as e:
            logger.error("Error: %s", e)
            raise HTTPException(status_code=400, detail=str(e)) from e

    @staticmethod
    def parse_user_attributes(user_data):
        """Parse the user attributes from the Cognito response"""
        parsed_data = {
            "username": user_data["Username"],
        }
        for attribute in user_data["UserAttributes"]:
            parsed_data[attribute["Name"]] = attribute["Value"]

        return parsed_data

    @staticmethod
    async def login(username, password):
        """Login a user with Cognito"""
        try:
            cognito_response = cognito_client.initiate_auth(
                ClientId=settings.AWS_COGNITO_CLIENT_ID,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            user_info = cognito_client.get_user(
                AccessToken=cognito_response['AuthenticationResult']['AccessToken']
            )
            parsed_data = CognitoService.parse_user_attributes(user_info)
            response_data = {
                "username": parsed_data['username'],
                "user_id": parsed_data['sub'],
                "first_name": parsed_data.get('given_name', ''),
                "last_name": parsed_data.get('family_name', ''),
                "email": parsed_data.get('email', ''),
                "age": parsed_data.get('custom:age', '0'),
                "onboardingCompleted": parsed_data.get('custom:onboardingCompleted', 'false')
            }
            response = JSONResponse(content=response_data)
            response.set_cookie(
                key="access_token",
                value=cognito_response['AuthenticationResult']['AccessToken'],
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=3600  # 1 hour
            )
            response.set_cookie(
                key="refresh_token",
                value=cognito_response['AuthenticationResult']['RefreshToken'],
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=2592000  # 30 days
            )
            return response
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @staticmethod
    async def logout(token):
        """Logout a user from Cognito"""
        try:
            cognito_client.global_sign_out(AccessToken=token)
            
            response = JSONResponse(content={"message": "User logged out successfully"})
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @staticmethod
    async def get_jwks():
        """Get the JWKS from the Cognito endpoint"""
        if time.time() - CognitoService.jwks_cache_timestamp > settings.JWKS_CACHE_TIMEOUT:
            async with httpx.AsyncClient() as client:
                response = await client.get(settings.KEYS_URL)
                CognitoService.jwks_cache = response.json()['keys']
            CognitoService.jwks_cache_timestamp = time.time()
        return CognitoService.jwks_cache

    @staticmethod
    async def decode_and_validate_token(token: str):
        """Decode and validate the JWT token"""
        try:
            headers = jwt.get_unverified_headers(token)
            kid = headers['kid']
            jwks = await CognitoService.get_jwks()
            key = next((k for k in jwks if k['kid'] == kid), None)
            if not key:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="Key not found")
            public_key = jwk.construct(key)
            payload = jwt.decode(
                token,
                public_key.to_pem(),
                options={'verify_exp': False, "verify_signature": False}
            )
            return TokenPayload(**payload)
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token") from e


    @staticmethod
    def get_current_user_id(token: str):
        """Get the current user ID from the JWT token"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.get_unverified_claims(token)
            username: str = payload.get("sub")
            return username
        except JWTError as e:
            raise credentials_exception from e

    @staticmethod
    def change_password(token, old_password, new_password):
        """Change the password of a user"""
        try:
            cognito_client.change_password(
                AccessToken=token,
                PreviousPassword=old_password,
                ProposedPassword=new_password
            )
            return {"message": "Password changed successfully"}
        except Exception as e:
            logger.error("Error: %s", e)
            raise HTTPException(status_code=400, detail=str(e)) from e

    @staticmethod
    def forgot_password(username):
        """Send a password reset code to the user's email"""
        try:
            cognito_client.forgot_password(
                ClientId=settings.AWS_COGNITO_CLIENT_ID,
                Username=username
            )
            return {"message": "Password reset code sent successfully"}
        except Exception as e:
            logger.error("Error: %s", e)
            raise HTTPException(status_code=400, detail=str(e)) from e

    @staticmethod
    def confirm_forgot_password(username, code, password):
        """Confirm the password reset with the confirmation code"""
        try:
            cognito_client.confirm_forgot_password(
                ClientId=settings.AWS_COGNITO_CLIENT_ID,
                Username=username,
                ConfirmationCode=code,
                Password=password
            )
            return {"message": "Password reset successfully"}
        except Exception as e:
            logger.error("Error: %s", e)
            raise HTTPException(status_code=400, detail=str(e)) from e

    @staticmethod
    def update_user_attributes(username, attributes):
        """Update the user attributes in Cognito"""
        try:
            cognito_client.admin_update_user_attributes(
                UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                Username=username,
                UserAttributes=[
                    {'Name': 'given_name', 'Value': attributes.get('firstName', '')},
                    {'Name': 'family_name', 'Value': attributes.get('lastName', '')},
                    {'Name': 'custom:age', 'Value': str(attributes.get('age', '0'))}
                ]
            )
            return {"message": "User attributes updated successfully"}
        except Exception as e:
            logger.error("Error: %s", e)
            raise HTTPException(status_code=400, detail=str(e)) from e

    @staticmethod
    def mark_onboarding_completed(username, attributes):
        """Update the user attributes in Cognito"""
        try:
            cognito_client.admin_update_user_attributes(
                UserPoolId=settings.AWS_COGNITO_USER_POOL_ID,
                Username=username,
                UserAttributes=[
                    {
                        'Name': 'custom:onboardingCompleted', 
                        'Value': str(attributes.get('onboardingCompleted', 'true'))
                    }
                ]
            )
            return {"message": "onboarding completed marked successfully"}
        except Exception as e:
            logger.error("Error: %s", e)
            raise HTTPException(status_code=400, detail=str(e)) from e
