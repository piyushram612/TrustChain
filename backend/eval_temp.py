import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import classification_report, precision_score, recall_score, f1_score
import os

sys.path.append('d:/projects/IOT-ML-Project/backend')
from train_model import load_intel_dataset, add_sigma_labels, FEATURE_COLS
import trust_enhancements

# Set up to write to text file
with open('d:/projects/IOT-ML-Project/backend/eval_output_utf8.txt', 'w', encoding='utf-8') as f:
    df = pd.read_csv('d:/projects/IOT-ML-Project/backend/sensor_dataset.csv')
    if 'temperature' in df.columns and 'humidity' in df.columns:
        df.columns = [c.lower().strip() for c in df.columns]

    f.write("Loading IF model...\n")
    iso_forest = joblib.load('d:/projects/IOT-ML-Project/backend/trust_model.pkl')
    n_feat = iso_forest.n_features_in_
    f.write(f"IF expects {n_feat} features.\n")

    f.write("Loading dataset...\n")
    df = load_intel_dataset('d:/projects/IOT-ML-Project/sensor_data.csv')
    f.write("Adding sigma labels...\n")
    df = add_sigma_labels(df, FEATURE_COLS)

    df = df.sample(n=100000, random_state=42)
    y_true = df['label'].values

    X = df[FEATURE_COLS].values
    X_if = X[:, :n_feat]

    f.write(f"Evaluating Isolation Forest with {n_feat} features...\n")
    y_pred_iso = iso_forest.predict(X_if)
    y_pred_iso = np.where(y_pred_iso == 1, 1, 0)
    report_iso = classification_report(y_true, y_pred_iso, target_names=["Malicious (0)", "Trusted (1)"], digits=4)
    f.write("-- Isolation Forest --\n")
    f.write(report_iso + "\n")

    f.write("Loading Ensemble Models...\n")
    trust_enhancements.MODEL_DIR = 'd:/projects/IOT-ML-Project/backend'
    trust_enhancements.load_extended_models()

    models = trust_enhancements._ensemble_models
    f.write(f"Found ensemble models: {list(models.keys())}\n")

    preds = []
    X_ens = X[:, :2]
    for name, model in models.items():
        p = model.predict(X_ens)
        preds.append(p)

    if len(preds) > 0:
        votes = np.array(preds)
        trusted_votes = (votes == 1).sum(axis=0)
        y_pred_ens = np.where(trusted_votes >= (len(models) / 2), 1, 0)
        report_ens = classification_report(y_true, y_pred_ens, target_names=["Malicious (0)", "Trusted (1)"], digits=4)
        f.write("-- Ensemble Models --\n")
        f.write(report_ens + "\n")
    else:
        f.write("No ensemble models found.\n")
