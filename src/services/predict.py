import pandas as pd
import numpy as np

# Text columns that were turned into 0/1 columns when the model was trained (see src/models/deal_pred.py)
CATEGORICAL = ['lead_source', 'industry', 'region', 'funding_stage']

def predict_sales(inputs: dict, model, columns: list) -> dict:
    '''
    Used by celery worker to predict user input with
    the provided (pretrained) model and its training columns
    '''
    df = pd.DataFrame([inputs]) # Model takes in df. Turn to df
    numeric = [c for c in df.columns if c not in CATEGORICAL]
    df[numeric] = df[numeric].astype(float) # None -> NaN, which the tree handles
    # Same 0/1 columns as training, in the same order. Missing dummy columns are 0
    df = pd.get_dummies(df, columns=CATEGORICAL, dtype=int).reindex(columns=columns, fill_value=0)

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
        "inputs": inputs, # The RAG step uses these to search for relevant tips
    }

    return report
