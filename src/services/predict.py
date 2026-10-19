import pandas as pd
import numpy as np

# Text columns that become 0/1 columns
CATEGORICAL = ['lead_source', 'industry', 'region', 'funding_stage']

def build_features(df: pd.DataFrame, columns: list | None = None) -> pd.DataFrame:
    '''
    Turns input rows into model columns. Training (src/pipeline/train.py) and
    prediction both use this, so the model always sees inputs built the same way.
    columns: the model's training columns. Missing 0/1 columns become 0
    '''
    df = df.copy()
    numeric = [c for c in df.columns if c not in CATEGORICAL]
    df[numeric] = df[numeric].astype(float) # None -> NaN, which the tree handles
    X = pd.get_dummies(df, columns=CATEGORICAL, dtype=int)
    return X if columns is None else X.reindex(columns=columns, fill_value=0)

def predict_sales(inputs: dict, model, columns: list, model_version: str = 'unknown') -> dict:
    '''
    Used by celery worker to predict user input with
    the provided (pretrained) model and its training columns
    '''
    df = build_features(pd.DataFrame([inputs]), columns) # Model takes in df. Turn to df

    answers = model.classes_
    probabilities = model.predict_proba(df)[0]
    sort = np.argsort(probabilities)[::-1] # Sort from greatest -> least

    report = { # For the RAG report
        "predicted_label": str(answers[sort[0]]), # Pred is a list. Use as index
        "class_probabilities": {
            str(label): round(float(prob), 4)
            for label, prob in zip(answers, probabilities)
        },
        "top_probability": round(float(probabilities[sort[0]]), 4),
        "second_best_label": str(answers[sort[1]]),
        "probability_margin": round(
            float(probabilities[sort[0]] - probabilities[sort[1]]),
            4,
        ),
        "model_version": model_version, # Which trained model answered, for tracing bad predictions
        "inputs": inputs, # The RAG step uses these to search for relevant tips
    }

    return report
