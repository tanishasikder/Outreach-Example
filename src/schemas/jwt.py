'''
Checks the JWT sent as "Authorization: Bearer <token>".
Make a token for local testing with:
    python -m src.schemas.jwt            # user "dev-user", valid 60 minutes
    python -m src.schemas.jwt alice 120
'''

import sys
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
ALGORITHM = 'HS256'

# auto_error=False so a missing header gives our 401 instead of FastAPI's 403
bearer = HTTPBearer(auto_error=False)

def unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={'WWW-Authenticate': 'Bearer'}
    )

def verify_jwt(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if credentials is None:
        raise unauthorized('Authorization is missing')
    if not SECRET_KEY:
        raise HTTPException(status_code=500, detail='JWT_SECRET_KEY is not set on the server')
    try:
        # decode checks the signature and the expiry time
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={'require': ['sub', 'exp']}
        )
    except InvalidTokenError:
        raise unauthorized('Invalid or expired token')
    return payload

def create_token(user_id: str, minutes: int = 60) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({'sub': user_id, 'exp': expires}, SECRET_KEY, algorithm=ALGORITHM)

if __name__ == '__main__':
    if not SECRET_KEY:
        sys.exit('JWT_SECRET_KEY is not set in .env')
    user = sys.argv[1] if len(sys.argv) > 1 else 'dev-user'
    minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    print(create_token(user, minutes))
