"""Predict whether a deal is won, lost or open, using the raw CSV columns as they are.

    python src/models/deal_pred.py                  # reads ./data/
    python src/models/deal_pred.py --data my_csvs   # folder with deals.csv and accounts.csv

Needs scikit-learn 1.3 or newer (the decision tree handles blank values itself, so nothing is filled in).
Each company has at most one deal, so "deal status" and "company status" are the same thing.
"""
import argparse
from pathlib import Path
# from imblearn.over_sampling import SMOTE
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text
import joblib

MODEL_DIR = Path(__file__).resolve().parent # Save next to this file, from any working directory

# Columns we do NOT feed to the model:
DROP = [
    "status",        # this is the answer we are predicting
    "deal_id",       # ID numbers carry no information about the company
    "account_id",
    "name",          # made-up company name, not informative
    "created_date",  # dates are text; turning them into numbers would be feature engineering
    "close_date",    # LEAK: blank exactly when the deal is open, filled in when it is won or lost
]

ap = argparse.ArgumentParser()
ap.add_argument("--data", default="data", help="folder with deals.csv and accounts.csv")
args = ap.parse_args()

# Put each deal next to its company's row, so every row has the deal columns and the company columns.
df = pd.read_csv(f"{args.data}/deals.csv").merge(pd.read_csv(f"{args.data}/accounts.csv"), on="account_id")

y = df["status"]
X = pd.get_dummies(df.drop(columns=DROP), dtype=int)   # text columns -> 0/1 columns (a model needs numbers)

# smote = SMOTE(random_state=42)
# 80% to learn from, 20% held back to test on. stratify keeps the won/lost/open mix the same in both.
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

#X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)

model = DecisionTreeClassifier(max_depth=2, random_state=42).fit(X_train, y_train)
pred = model.predict(X_test)

baseline = (y_test == y_train.mode()[0]).mean()        # accuracy of always guessing the most common status
print(f"train: {len(X_train)} deals   test: {len(X_test)} deals "
    f"(open deals in test: {(y_test == 'open').sum()})")
print(f"\ntest accuracy: {accuracy_score(y_test, pred):.3f}   (always guessing '{y_train.mode()[0]}' gets {baseline:.3f})")

labels = sorted(y.unique())
print("\nconfusion matrix (rows = what really happened, columns = what the model said):")
print(pd.DataFrame(confusion_matrix(y_test, pred, labels=labels),
                index=[f"real {c}" for c in labels], columns=[f"said {c}" for c in labels]))
print("\n" + classification_report(y_test, pred, digits=2, zero_division=0))

print("the model's rules:")
print(export_text(model, feature_names=list(X.columns)))
joblib.dump(model, MODEL_DIR / 'sales_pred_model.joblib')
# The API must build its input with exactly these columns, in this order (see the get_dummies/reindex step in src/services/predict.py).
joblib.dump(list(X.columns), MODEL_DIR / 'model_columns.joblib')