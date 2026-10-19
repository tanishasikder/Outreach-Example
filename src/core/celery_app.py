'''
Celery worker. Start it from the project root (--pool=solo is needed on Windows):
    celery -A src.core.celery_app worker -Q queue_sales,queue_rag --pool=solo -l info

The API sends each upload as a chain: process_input (prediction) -> process_rag (report).
'''

import logging
import time
from celery import Celery
from celery.signals import worker_process_init
from .config import Settings, MODEL_REFRESH_SECONDS
from . import model_registry
from src.services.predict import predict_sales

celery_app = Celery('outreachproject')
celery_app.config_from_object(Settings)

logger = logging.getLogger(__name__)

# Loaded once per worker process. The worker is a separate process from
# FastAPI, so it loads its own copies instead of using app.state
_models = {}

def get_sales_model():
    '''
    Returns (version, model, columns) for the live model. Every MODEL_REFRESH_SECONDS
    it checks models/latest.json, so a model promoted by Airflow is picked up
    without restarting the worker
    '''
    cached = _models.get('sales')
    if cached and time.monotonic() - cached['checked'] < MODEL_REFRESH_SECONDS:
        return cached['version'], cached['model'], cached['columns']
    try:
        info = model_registry.latest()
        version = info['version'] if info else model_registry.BUNDLED
        if not cached or cached['version'] != version:
            model, columns = model_registry.load(version)
            cached = {'version': version, 'model': model, 'columns': columns}
            logger.info('Loaded sales model %s', version)
    except Exception:
        if not cached:
            raise # Nothing to fall back to
        # Storage is unreachable: keep answering with the model we already have
        logger.exception('Could not check for a new model, keeping %s', cached['version'])
    cached['checked'] = time.monotonic()
    _models['sales'] = cached
    return cached['version'], cached['model'], cached['columns']

def get_rag_models():
    if 'rag' not in _models:
        # Imported here so the API (which only queues tasks) doesn't load them
        from src.models.rag_models import get_llm
        from src.models.vector import get_client
        _models['rag'] = (get_llm(), get_client())
    return _models['rag']

@worker_process_init.connect
def load_model(**kwargs):
    # Runs in each worker process (prefork pool). With --pool=solo the
    # models load on the first task instead
    get_sales_model()

@celery_app.task(name='predict-sales', queue='queue_sales')
def process_input(inputs: dict) -> dict:
    version, model, columns = get_sales_model()
    return predict_sales(inputs, model, columns, version)

@celery_app.task(name='rag-output', queue='queue_rag')
def process_rag(report: dict) -> dict:
    # Gets the prediction from process_input. If the report fails,
    # still return the prediction so the user sees something useful
    try:
        from src.services.rag import make_output
        llm, client = get_rag_models()
        return {**report, 'report': make_output(report, llm, client)}
    except Exception:
        logger.exception('RAG report failed')
        return {**report, 'report': None, 'report_error': 'The sales report could not be generated.'}
