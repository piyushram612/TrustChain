import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest

# --- CONFIGURATION ---
DATA_FILE = "sensor_data.csv"
MODEL_FILE = "trust_model.pkl"

def train_model():
    print(f" Loading Real-World Data from {DATA_FILE}...")

    try:
        # 1. READ DATA CORRECTLY (Handle Space Separation)
        # The Intel dataset uses spaces, not commas. It also has no header row.
        # We manually assign the column names: date, time, epoch, moteid, temp, humidity, light, voltage
        df = pd.read_csv(DATA_FILE, sep='\s+', header=None, on_bad_lines='skip')
        
        # Manually name the columns based on Intel Lab documentation
        df.columns = ['date', 'time', 'epoch', 'moteid', 'temperature', 'humidity', 'light', 'voltage']
        
        print(f" Loaded {len(df)} rows.")

    except Exception as e:
        print(f" Error loading CSV: {e}")
        return

    # 2. CLEAN THE DATA (Crucial Step)
    # The raw dataset has some noise (e.g., temps like 122°C or -5°C which are sensor errors).
    # We filter to keep only "Normal" Room Temperatures (15°C to 40°C)
    # This ensures our model learns what "Safe" looks like.
    print(" Cleaning data (removing sensor errors)...")
    df = df[(df['temperature'] > 15) & (df['temperature'] < 40)]
    df = df[(df['humidity'] > 0) & (df['humidity'] < 100)]
    
    print(f" Training on {len(df)} valid 'Normal' data points.")

    # 3. SELECT FEATURES
    X_train = df[['temperature', 'humidity']].values

    # 4. TRAIN THE MODEL
    print(" Training Isolation Forest...")
    # contamination=0.01 means we assume 1% of this data might still be outliers
    model = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
    model.fit(X_train)

    # 5. SAVE THE MODEL
    joblib.dump(model, MODEL_FILE)
    print(f" Model saved to {MODEL_FILE}")

    # --- VERIFICATION ---
    print("\n---  TEST RESULTS ---")
    
    # Test Normal (Should be Trusted)
    normal_val = [[24.5, 45.0]]
    pred_normal = model.predict(normal_val)[0]
    print(f"Input: {normal_val} -> {'✅ Trusted' if pred_normal == 1 else '❌ Malicious'}")

    # Test Attack (Should be Malicious)
    attack_val = [[110.0, 5.0]]
    pred_attack = model.predict(attack_val)[0]
    print(f"Input: {attack_val} -> {'✅ Trusted' if pred_attack == 1 else '⚠️ THREAT BLOCKED'}")

if __name__ == "__main__":
    train_model()