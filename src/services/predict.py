import pandas as pd
import numpy as np
from fastapi import Request

def predict_sales(input : dict, model, gem_model, hug_model):
    '''
    Used by celery worker to predict user input with
    the provide (pretrained) model
    '''
    df = pd.read_json([input]) # Model takes in df. Turn to df
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
    }

    return report

