import base64
from celery import Celery
from celery.signals import worker_process_init
from .config import Settings
celery_app = Celery('outreachproject')

celery_app.config_from_object(Settings)

celery_app.conf.task_routes = {
    'predict-sales' : {'queue' : 'queue_sales'}
}
image_model = None

def get_model():
    global 
