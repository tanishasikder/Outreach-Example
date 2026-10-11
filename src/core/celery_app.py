import base64
from celery import Celery
from celery.signals import worker_process_init
from .config import Settings
celery_app = Celery('outreachproject')
from fastapi import Request
from src.services.predict import predict_sales
celery_app.config_from_object(Settings)

model, gem_model, hug_model = None, None, None

def get_models(request: Request):
    global model, gem_model, hug_model
    if model is None:
        model = request.app.state.image_model
        gem_model = request.app.state.gem_model
        hug_model = request.app.state.gem_model
    return model, gem_model, hug_model

@worker_process_init.connect
def load_model(**kwargs):
    get_models()

@celery_app.task(name='predict-sales', queue='queue_sales')
def process_input(inputs : dict):
    return predict_sales(get_models(), inputs)

@celery_app.task(name='rag-output', queue='queue_rag')
def process_rag(inputs : dict):
    return 
    