'''
Celery worker. Start it from the project root (--pool=solo is needed on Windows):
    celery -A src.core.celery_app worker -Q queue_sales,queue_rag --pool=solo -l info

The API sends each upload as a chain: process_input (prediction) -> process_rag (report).
'''

import logging
import joblib
from celery import Celery
from celery.signals import worker_process_init
from .config import Settings, MODEL_PATH, COLUMNS_PATH
from src.services.predict import predict_sales

celery_app = Celery('outreachproject')
celery_app.config_from_object(Settings)

logger = logging.getLogger(__name__)

# Loaded once per worker process. The worker is a separate process from
# FastAPI, so it loads its own copies instead of using app.state
_models = {}

def get_sales_model():
    if 'sales' not in _models:
        _models['sales'] = (joblib.load(MODEL_PATH), joblib.load(COLUMNS_PATH))
    return _models['sales']

def get_rag_models():
    if 'rag' not in _models:
        # Imported here so the API (which only queues tasks) doesn't load them
        from src.models.rag_models import get_gem_model
        from src.models.vector import get_client
        _models['rag'] = (get_gem_model(), get_client())
    return _models['rag']

@worker_process_init.connect
def load_model(**kwargs):
    # Runs in each worker process (prefork pool). With --pool=solo the
    # models load on the first task instead
    get_sales_model()

@celery_app.task(name='predict-sales', queue='queue_sales')
def process_input(inputs: dict) -> dict:
    model, columns = get_sales_model()
    return predict_sales(inputs, model, columns)

@celery_app.task(name='rag-output', queue='queue_rag')
def process_rag(report: dict) -> dict:
    # Gets the prediction from process_input. If the report fails,
    # still return the prediction so the user sees something useful
    try:
        from src.services.rag import make_output
        gem_model, client = get_rag_models()
        return {**report, 'report': make_output(report, gem_model, client)}
    except Exception:
        logger.exception('RAG report failed')
        return {**report, 'report': None, 'report_error': 'The sales report could not be generated.'}
