'''
Settings shared by the API and the Celery worker. Values come from .env.

Redis: REDIS_URL (e.g. redis://localhost:6379). Each use gets its own
Redis database number so their keys never mix.
'''

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from dotenv import load_dotenv
import os

load_dotenv()

# Paths are relative to the project root, so it works from any working directory
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / 'data' / 'data.duckdb'
MODEL_PATH = BASE_DIR / 'src' / 'models' / 'sales_pred_model.joblib'
COLUMNS_PATH = BASE_DIR / 'src' / 'models' / 'model_columns.joblib'

# Files shared between the pipeline (Airflow) and the app: trained models and data snapshots.
# On AWS this is the S3 bucket. Without S3_BUCKET (local dev) it is the artifacts/ folder
S3_BUCKET = os.getenv('S3_BUCKET', '')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
LOCAL_ARTIFACTS_DIR = BASE_DIR / 'artifacts'

# dbt's warehouse. Separate from DB_PATH so the pipeline never fights the API for the DuckDB lock
WAREHOUSE_PATH = Path(os.getenv('DUCKDB_PATH', BASE_DIR / 'data' / 'warehouse.duckdb'))

# How often the worker checks for a newly promoted model
MODEL_REFRESH_SECONDS = int(os.getenv('MODEL_REFRESH_SECONDS', '300'))

# Pages allowed to call the API from a browser (comma separated in .env)
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5500,http://127.0.0.1:5500').split(',')

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

def redis_db_url(db: int) -> str:
    # Replace any /<db> already in REDIS_URL with the one we want
    parts = urlsplit(REDIS_URL)
    return urlunsplit((parts.scheme, parts.netloc, f'/{db}', parts.query, parts.fragment))

BROKER_URL = redis_db_url(0)        # Celery task queue
RESULT_BACKEND_URL = redis_db_url(1) # Celery task results (read by /status)
LIMITER_URL = redis_db_url(2)       # slowapi rate limit counters


class Settings:
    '''Celery config, loaded with celery_app.config_from_object(Settings)'''
    broker_url = BROKER_URL
    result_backend = RESULT_BACKEND_URL
    broker_connection_retry_on_startup = True # Keep retrying if Redis starts after the worker

    # Only JSON (no pickle) goes through Redis
    task_serializer = 'json'
    result_serializer = 'json'
    accept_content = ['json']

    task_track_started = True # Status shows STARTED while a task runs, not just PENDING
    result_expires = 3600     # Delete results from Redis after 1 hour
