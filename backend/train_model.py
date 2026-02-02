import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest

# 1. Generate Synthetic Training Data
np.random.seed(42)
n_samples = 1000

# Generate "Good" Data
X_good = pd.DataFrame({
    'temperature': np.random.normal(loc=25, scale=3, size=n_samples), 
    'humidity': np.random.normal(loc=50, scale=5, size=n_samples),
    'label': 'Trusted' # We add this label just for the CSV file readability
})

# Generate "Bad" Data
X_bad = pd.DataFrame({
    'temperature': np.random.uniform(low=80, high=120, size=50), 
    'humidity': np.random.uniform(low=0, high=10, size=50),
    'label': 'Malicious'
})

# Combine them
X_final = pd.concat([X_good, X_bad], ignore_index=True)

# --- SAVE TO CSV (So you can see it) ---
X_final.to_csv('sensor_dataset.csv', index=False)
print("Dataset created and saved as 'sensor_dataset.csv'")

# 2. Train the Model (We drop the 'label' column because ML learns patterns, not answers)
model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
model.fit(X_final[['temperature', 'humidity']])

# 3. Save the Model
joblib.dump(model, 'trust_model.pkl')
print("Model trained and saved as 'trust_model.pkl'")