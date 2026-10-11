import jwt
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.environ.get('JWT_SECRET_KEY')

def verify_jwt(token: str):
    try:
        payload = jwt.encode(
            token,
            SECRET_KEY,
            algorithms=["HS256"]
        )

        return payload
    except InvalidTokenError as e:
        print(f"Token validation failed: {e}")
        return None