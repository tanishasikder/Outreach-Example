'''
Versioned sales models, stored with src/core/storage.py:

    models/<version>/model.joblib      the trained model
    models/<version>/columns.joblib    its input columns, in order
    models/<version>/metrics.json      how it scored when it was trained
    models/<version>/training_data.parquet   the exact data it learned from
    models/latest.json                 which version is live (the "production" pointer)

Airflow writes new versions and moves the pointer (src/pipeline/).
The Celery worker follows the pointer (src/core/celery_app.py).
'''

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib

from . import storage
from .config import MODEL_PATH, COLUMNS_PATH

LATEST_KEY = 'models/latest.json'
CACHE_DIR = Path(tempfile.gettempdir()) / 'outreach-models'
BUNDLED = 'bundled' # The model files committed in src/models/, used until a pipeline run promotes one

def key(version: str, name: str) -> str:
    return f'models/{version}/{name}'

def new_version() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

def latest() -> dict | None:
    '''The live version's info, or None if nothing has been promoted yet'''
    return storage.read_json(LATEST_KEY)

def load(version: str):
    '''Returns (model, columns) for a version'''
    if version == BUNDLED:
        return joblib.load(MODEL_PATH), joblib.load(COLUMNS_PATH)
    folder = CACHE_DIR / version
    files = {}
    for name in ['model.joblib', 'columns.joblib']:
        path = folder / name
        if not path.exists(): # Versions never change, so a cached download stays valid
            storage.download(key(version, name), path)
        files[name] = joblib.load(path)
    return files['model.joblib'], files['columns.joblib']

def load_live():
    '''Returns (version, model, columns) for the version in latest.json, or the bundled model'''
    info = latest()
    version = info['version'] if info else BUNDLED
    model, columns = load(version)
    return version, model, columns

def save(version: str, model, columns: list, metrics: dict, training_parquet: Path):
    with tempfile.TemporaryDirectory() as tmp:
        for name, obj in [('model.joblib', model), ('columns.joblib', columns)]:
            path = Path(tmp) / name
            joblib.dump(obj, path)
            storage.upload(path, key(version, name))
    storage.upload(training_parquet, key(version, 'training_data.parquet'))
    storage.write_json(key(version, 'metrics.json'), metrics)

def metrics(version: str) -> dict | None:
    return storage.read_json(key(version, 'metrics.json'))

def promote(version: str, reason: str):
    storage.write_json(LATEST_KEY, {
        'version': version,
        'promoted_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'reason': reason,
        'metrics': metrics(version),
    })
