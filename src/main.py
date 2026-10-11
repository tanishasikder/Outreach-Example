'''
Start from the project root:
    uvicorn src.main:app --reload
'''

import duckdb
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.core.config import DB_PATH, CORS_ORIGINS
from src.core.limiter import limiter
from src.database import initialize
from src.routers import input

# The API only validates input and queues work. The sales model and the
# RAG models are loaded by the Celery worker (src/core/celery_app.py)
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = duckdb.connect(str(DB_PATH))
    initialize(app.state.db)
    yield
    app.state.db.close() # Clean up after

app = FastAPI(lifespan=lifespan)

# slowapi needs the limiter on app.state, and a handler to turn the limit into a 429
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(input.router)
