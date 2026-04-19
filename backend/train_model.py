import pandas as pd
import numpy as np
import joblib
import os
from sklearn.ensemble import IsolationForest

# --- CONFIGURATION ---
INTEL_DATA_FILE = "sensor_data.csv"        # Intel Lab IoT dataset (space-separated, no header)
FALLBACK_DATA_FILE = "sensor_dataset.csv"  # Original small CSV fallback
MODEL_FILE = "trust_model.pkl"

FEATURE_COLS = ['temperature', 'humidity', 'light', 'voltage']


def load_intel_dataset(path):
    """
    Load the Intel Lab IoT dataset.
    Format: space-separated, no header row.
    Columns: date, time, epoch, moteid, temperature, humidity, light, voltage
    """
    col_names = ['date', 'time', 'epoch', 'moteid',
                 'temperature', 'humidity', 'light', 'voltage']
    df = pd.read_csv(path, sep=' ', header=None, names=col_names,
                     on_bad_lines='skip')

    # Combine date + time into a single datetime column, drop originals
    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'],
                                    errors='coerce')
    df.drop(columns=['date', 'time'], inplace=True)

    # Convert sensor readings to numeric, coercing errors to NaN
    for col in FEATURE_COLS:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Drop rows with any NaN in sensor columns or datetime
    df.dropna(subset=FEATURE_COLS + ['datetime'], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def load_fallback_dataset(path):
    """
    Load the original sensor_dataset.csv (comma-separated, has header).
    Returns a dataframe with temperature, humidity columns and a label column.
    """
    df = pd.read_csv(path)
    df.columns = [c.lower().strip() for c in df.columns]
    # Ensure required columns exist
    if 'label' not in df.columns:
        # If no label column exists, treat all rows as trusted
        df['label'] = 1
    return df


def add_sigma_labels(df, feature_cols):
    """
    3-Sigma statistical anomaly labeling.
    For each row: if ANY sensor column deviates > 3 std from column mean → label 0 (malicious).
    Otherwise label 1 (trusted).
    """
    means = df[feature_cols].mean()
    stds  = df[feature_cols].std()

    # Boolean mask: True where ANY column is an outlier
    outlier_mask = ((df[feature_cols] - means).abs() > 3 * stds).any(axis=1)
    df['label'] = np.where(outlier_mask, 0, 1)
    return df

def train_model():
    # --- 1. LOAD DATASET (Intel or fallback) ---
    using_intel = False
    if os.path.exists(INTEL_DATA_FILE):
        print(f" Loading Intel Lab IoT Dataset from '{INTEL_DATA_FILE}'...")
        try:
            df = load_intel_dataset(INTEL_DATA_FILE)
            print(f" Loaded {len(df)} valid rows from Intel dataset.")
            using_intel = True
        except Exception as e:
            print(f" [WARNING] Failed to load Intel dataset ({e}). Falling back to '{FALLBACK_DATA_FILE}'.")
    
    if not using_intel:
        print(f" [WARNING] Intel dataset not found. Using fallback: '{FALLBACK_DATA_FILE}'")
        try:
            df = load_fallback_dataset(FALLBACK_DATA_FILE)
            print(f" Loaded {len(df)} rows from fallback dataset.")
        except Exception as e:
            print(f" Error loading fallback CSV: {e}")
            return

    # --- 2. PROGRAMMATIC LABELING (3-Sigma Anomaly Detection) ---
    if using_intel:
        print(" Generating 3-sigma anomaly labels...")
        df = add_sigma_labels(df, FEATURE_COLS)
        label_counts = df['label'].value_counts()
        print(f"   -> Trusted (1): {label_counts.get(1, 0)} | Malicious (0): {label_counts.get(0, 0)}")

    # --- 3. SAMPLE 50,000 ROWS (for performance) ---
    if len(df) > 50000:
        print(f" Sampling 50,000 rows (from {len(df)}) for reproducibility...")
        df = df.sample(n=50000, random_state=42)
        df.reset_index(drop=True, inplace=True)

    # --- 4. CLEAN / SELECT FEATURES ---
    if using_intel:
        # For Intel data use all 4 sensor features
        available_features = [c for c in FEATURE_COLS if c in df.columns]
        df_clean = df.dropna(subset=available_features)
        print(f" Training on {len(df_clean)} valid data points (features: {available_features}).")
        X_train = df_clean[available_features].values
    else:
        # Fallback: only temperature + humidity (original behaviour)
        df_clean = df[(df['temperature'] > 15) & (df['temperature'] < 40)]
        df_clean = df_clean[(df_clean['humidity'] > 0) & (df_clean['humidity'] < 100)]
        print(f" Training on {len(df_clean)} valid 'Normal' data points.")
        X_train = df_clean[['temperature', 'humidity']].values

    # --- 5. TRAIN ISOLATION FOREST ---
    print(" Training Isolation Forest...")
    # contamination=0.01 means we assume ~1% of this data might still be outliers
    model = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
    model.fit(X_train)

    # --- 6. SAVE THE MODEL ---
    joblib.dump(model, MODEL_FILE)
    print(f" Model saved to '{MODEL_FILE}'")

    # --- ENHANCEMENTS: TRAIN EXTRA MODELS ---
    import trust_enhancements
    # Extra ensemble models are trained on 2-feature slice for compatibility with app.py
    trust_enhancements.train_extra_models(X_train[:, :2])

    # --- VERIFICATION ---
    print("\n---  TEST RESULTS ---")
    n_feat = model.n_features_in_

    # Test Normal (Should be Trusted): temp=24.5, hum=45, light=200, voltage=2.7
    normal_base = [24.5, 45.0, 200.0, 2.7]
    normal_val  = [normal_base[:n_feat]]
    pred_normal = model.predict(normal_val)[0]
    print(f"Input: {normal_val} -> {'Trusted' if pred_normal == 1 else 'Malicious'}")

    # Test Attack (Should be Malicious): extreme temp + humidity
    attack_base = [110.0, 5.0, 0.0, 0.5]
    attack_val  = [attack_base[:n_feat]]
    pred_attack = model.predict(attack_val)[0]
    print(f"Input: {attack_val} -> {'Trusted' if pred_attack == 1 else 'THREAT BLOCKED'}")

if __name__ == "__main__":
    train_model()