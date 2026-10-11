from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi import Request, status, Body
from fastapi import Depends
import json

from pydantic import ValidationError
from core.limiter import limiter
from src.schemas.jwt import verify_jwt
from src.schemas.validate import UploadVerify
# No prefix since the frontend calls /upload and /status directly
router = APIRouter()

# Basic health check to ensure server is functioning
@router.get("/health")
def root():
    return {"status" : "OK"}

@router.post("/upload")
@limiter.limit("3/minute")
async def upload(
        request: Request,
        payload: dict = Depends(verify_jwt),
        info: str = Form(...)
    ):
    '''
    Endpoint for user input. Inputs for company data to
    see if the company will buy, reject, or be idle.
    Verified by Pydantic in schemas/validate
    '''
    try:
       # Verify the user first
        user_id = payload['sub']
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Authorization is missing',
                headers={'WWW-Authenticate': 'Bearer'}
            )
        info = json.loads(info)
        validated = UploadVerify.model_validate(info)
        return validated
    except (json.JSONDecodeError, ValidationError):
        raise HTTPException(
            status_code=422,
            detail="Invalid upload metadata"
        )
