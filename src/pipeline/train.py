'''
Trains a candidate sales model from the dbt table deal_training, scores it and the
live model on the same held-out deals, and saves it as a new version (not live yet).
The last line printed is the version, which Airflow passes to promote.py.

    python -m src.pipeline.train
    python -m src.pipeline.train --max-depth 4
'''

import argparse
import json
import sys
import tempfile
from enum import Enum
from pathlib import Path

import duckdb
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

from src.core import model_registry
from src.core.config import WAREHOUSE_PATH
from src.schemas.validate import UploadVerify
from src.services.predict import CATEGORICAL, build_features

# The model learns from exactly the fields the API accepts, so every
# prediction request has every column the model was trained on
FEATURES = list(UploadVerify.model_fields)
TARGET = 'status'

def load_training_data() -> pd.DataFrame:
    with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as con:
        # ORDER BY: DuckDB returns rows in any order, which would change the train/test
        # split (and the scores) on every run even with random_state fixed
        return con.sql(f"SELECT {', '.join(FEATURES)}, {TARGET} FROM deal_training ORDER BY deal_id").df()

def check_categories(df: pd.DataFrame):
    '''Stops if the data has a category the API would reject (dbt vars and validate.py out of sync)'''
    for col in CATEGORICAL:
        allowed = {e.value for e in UploadVerify.model_fields[col].annotation if isinstance(e, Enum)}
        unknown = set(df[col].dropna()) - allowed
        if unknown:
            sys.exit(f'{col} has values the API does not accept: {sorted(unknown)}. '
                     f'Update src/schemas/validate.py and dbt/dbt_project.yml together.')

def score(model, columns, test: pd.DataFrame) -> dict:
    pred = model.predict(build_features(test[FEATURES], columns))
    return {
        'accuracy': round(float(accuracy_score(test[TARGET], pred)), 4),
        'macro_f1': round(float(f1_score(test[TARGET], pred, average='macro', zero_division=0)), 4),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-depth', type=int, default=2)
    ap.add_argument('--max-features', default='sqrt')
    ap.add_argument('--test-size', type=float, default=0.2)
    args = ap.parse_args()

    df = load_training_data()
    check_categories(df)

    # 80% to learn from, 20% held back to test on. stratify keeps the won/lost/open mix the same in both
    train, test = train_test_split(df, test_size=args.test_size, stratify=df[TARGET], random_state=42)

    X_train = build_features(train[FEATURES])
    columns = list(X_train.columns)
    params = {'max_depth': args.max_depth, 'max_features': args.max_features, 'random_state': 42}
    model = DecisionTreeClassifier(**params).fit(X_train, train[TARGET])

    majority = train[TARGET].mode()[0]
    metrics = {
        **score(model, columns, test),
        'baseline_accuracy': round(float((test[TARGET] == majority).mean()), 4), # always guessing the most common status
        'params': params,
        'rows': {'train': len(train), 'test': len(test)},
        'class_counts': df[TARGET].value_counts().to_dict(),
    }

    # Score the model that is live right now on the SAME test deals, so promote.py compares fairly
    try:
        live_version, live_model, live_columns = model_registry.load_live()
        metrics['live'] = {'version': live_version, **score(live_model, live_columns, test)}
    except Exception as e:
        print(f'Could not score the live model ({e}); it will not be compared', file=sys.stderr)

    version = model_registry.new_version()
    with tempfile.TemporaryDirectory() as tmp:
        parquet = Path(tmp) / 'training_data.parquet'
        with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as con:
            con.execute(f"COPY deal_training TO '{parquet.as_posix()}' (FORMAT parquet)")
        model_registry.save(version, model, columns, metrics, parquet)

    print(json.dumps(metrics, indent=2), file=sys.stderr)
    print(version) # Last line of output: Airflow reads it

if __name__ == '__main__':
    main()
