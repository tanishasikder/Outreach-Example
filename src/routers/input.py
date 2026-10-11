import json
from fastapi import APIRouter, Form, HTTPException
from fastapi import Request, status
from fastapi import Depends
from fastapi.concurrency import run_in_threadpool
from celery import chain
from celery.result import AsyncResult
from kombu.exceptions import OperationalError
from redis import Redis
from redis.exceptions import RedisError

from pydantic import ValidationError
from src.core.config import BROKER_URL
from src.core.limiter import limiter
from src.core.celery_app import celery_app, process_input, process_rag
from src.schemas.jwt import verify_jwt
from src.schemas.validate import UploadVerify
# No prefix since the frontend calls /upload and /status directly
router = APIRouter()

QUEUE_DOWN = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail='The task queue (Redis) is not available. Try again shortly.'
)
QUEUE_ERRORS = (OperationalError, RedisError, RuntimeError) # RuntimeError: Celery's result store gave up reconnecting

def check_queue():
    # Fail fast with a 503. If Celery itself finds Redis down, it retries for
    # a long time and its result store can get stuck until the API restarts
    try:
        Redis.from_url(BROKER_URL, socket_connect_timeout=1, socket_timeout=1).ping()
    except RedisError:
        raise QUEUE_DOWN

# Basic health check to ensure server is functioning
@router.get("/health")
def root():
    return {"status" : "OK"}

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def upload(
        request: Request,
        payload: dict = Depends(verify_jwt), # 401 if the token is missing or invalid
        info: str = Form(...)
    ):
    '''
    Endpoint for user input. Inputs for company data to
    see if the company will buy, reject, or be idle.
    Verified by Pydantic in schemas/validate.
    Queues the prediction + report and returns a task_id for /status
    '''
    try:
        validated = UploadVerify.model_validate_json(info) # Parses the JSON and validates it
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=json.loads(e.json(include_url=False)) # Says which field is wrong
        )

    data = validated.model_dump(mode='json')
    await run_in_threadpool(check_queue)
    try:
        # Prediction first, then its output goes to the RAG report
        result = await run_in_threadpool(
            chain(process_input.s(data), process_rag.s()).apply_async
        )
    except QUEUE_ERRORS:
        raise QUEUE_DOWN
    return {"task_id": result.id, "status": "PENDING"}

@router.get("/status/{task_id}")
def task_status(task_id: str, payload: dict = Depends(verify_jwt)):
    '''
    Status of a task from /upload: PENDING, STARTED, SUCCESS or FAILURE.
    On SUCCESS, result has the prediction and the report
    '''
    check_queue()
    task = AsyncResult(task_id, app=celery_app)
    try:
        state = task.state
        body = {"task_id": task_id, "status": state}
        if state == 'SUCCESS':
            body["result"] = task.result
        elif state == 'FAILURE':
            body["error"] = "The prediction job failed."
    except QUEUE_ERRORS:
        raise QUEUE_DOWN
    return body
