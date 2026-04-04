import numpy as np
import random
import joblib
import os
from sklearn.svm import OneClassSVM
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier

# Global configuration
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))

# Global store for time-weighted reputation
# Dictionary mapping sensor_id -> reputation score
reputations = {}

def get_reputation(sensor_id):
    """
    Returns the current reputation for a given sensor_id.
    Default reputation = 0.5.
    """
    return reputations.get(sensor_id, 0.5)

def update_reputation(sensor_id, new_result, alpha=0.3):
    """
    Updates the reputation using exponential smoothing:
    new_rep = alpha * new_result + (1 - alpha) * old_rep
    """
    old_rep = get_reputation(sensor_id)
    new_rep = alpha * new_result + (1 - alpha) * old_rep
    reputations[sensor_id] = new_rep
    return new_rep

def simulate_attack(data, probability=0.1):
    """
    Randomly inject noise into input data with a configurable probability.
    Marks whether data is attacked or normal.
    """
    is_attacked = False
    new_data = data.copy()
    
    # Check if attack should be injected
    if random.random() < probability:
        is_attacked = True
        # Inject heavy noise to explicitly act as an attack
        if 'temperature' in new_data:
            new_data['temperature'] += random.uniform(50, 100)
        if 'humidity' in new_data:
            new_data['humidity'] = max(0, new_data['humidity'] - random.uniform(20, 40))
            
    return new_data, is_attacked

# --- ENSEMBLE AND SVM LOGIC ---
_ensemble_models = {}
_svm_model = None

def load_extended_models():
    """
    Load the supplementary models from disk if available.
    Expects svm_model.pkl, rf_model.pkl, knn_model.pkl, mlp_model.pkl
    """
    global _svm_model, _ensemble_models
    
    svm_path = os.path.join(MODEL_DIR, "svm_model.pkl")
    if os.path.exists(svm_path):
        _svm_model = joblib.load(svm_path)
        
    for name in ['rf', 'knn', 'mlp']:
        path = os.path.join(MODEL_DIR, f"{name}_model.pkl")
        if os.path.exists(path):
            _ensemble_models[name] = joblib.load(path)

def get_composite_trust_score(features, sensor_id, lambda_weight=0.5):
    """
    Calculates the composite trust score using SVM decision output scaled by a sigmoid,
    and then combined with the reputation score.
    Cs = (1 - lambda) * Ds + lambda * Rs
    """
    if _svm_model is None:
        return 0.5 # Default fallback
    
    # SVM decision function output
    svm_output = _svm_model.decision_function(features)[0]
    
    # Apply sigmoid scaling to map distance strictly between 0 and 1
    # Using np.expit equivalent: 1 / (1 + exp(-x))
    # We multiply by 5 to spread the typical SVM (-1 to 1) distance over the 0-1 scale smoothly
    ds = 1 / (1 + np.exp(-svm_output * 5))
    
    # Get current reputation
    rs = get_reputation(sensor_id)
    
    # Combine
    cs = (1 - lambda_weight) * ds + lambda_weight * rs
    return cs

def trigger_ensemble_validation(features):
    """
    Use at least 3 models (KNN, RandomForest, MLP) and implement majority voting.
    Returns 1 for trusted (normal), 0 for malicious (anomaly).
    """
    if not _ensemble_models:
        return 1 # Fallback to true if models missing
    
    votes = []
    for name, model in _ensemble_models.items():
        try:
            pred = model.predict(features)[0]
            votes.append(pred) # Assuming 1 is normal, 0/(-1) is anomaly
        except:
            continue
            
    if not votes:
        return 1
        
    # Majority voting (assuming 1 is positive class/trusted)
    # If 1 is normal and 0 is anomaly:
    trusted_votes = sum([1 for v in votes if v == 1])
    if trusted_votes >= (len(votes) / 2):
        return 1
    else:
        return 0

def get_explanation():
    """
    If the model supports feature_importances_, expose feature importance.
    """
    explanation = {}
    rf = _ensemble_models.get('rf')
    if rf and hasattr(rf, 'feature_importances_'):
        importances = rf.feature_importances_
        explanation['importance'] = {
            'temperature': importances[0] if len(importances) > 0 else 0,
            'humidity': importances[1] if len(importances) > 1 else 0
        }
    return explanation

def train_extra_models(X_train):
    """
    Given normal training data, synthesizes anomalous data and trains SVM, RF, KNN, and MLP models.
    Persists them to disk.
    """
    print(" [Enhancements] Training Supplemental Models (SVM, KNN, RF, MLP)...")
    
    # 1. Train Unsupervised One-Class SVM on Normal Data
    svm = OneClassSVM(nu=0.01)
    svm.fit(X_train)
    joblib.dump(svm, os.path.join(MODEL_DIR, "svm_model.pkl"))
    print("   -> Trained & Saved SVM (svm_model.pkl)")
    
    # 2. Prepare Supervised Dataset (Normal + Synthetic Anomalies) for Ensemble
    # Label: 1 = Normal, 0 = Anomaly
    y_normal = np.ones(len(X_train))
    
    # Generate some extreme outliers (temperature > 50, humidity < 10)
    np.random.seed(42)
    num_anomalies = max(min(100, len(X_train)), len(X_train) // 5)
    X_anom = np.column_stack((
        np.random.uniform(50, 120, size=num_anomalies), # Extreme Temp
        np.random.uniform(0, 10, size=num_anomalies)    # Extreme Humidity
    ))
    y_anom = np.zeros(num_anomalies)
    
    X_all = np.vstack((X_train, X_anom))
    y_all = np.concatenate((y_normal, y_anom))
    
    # 3. Train KNN
    knn = KNeighborsClassifier(n_neighbors=3)
    knn.fit(X_all, y_all)
    joblib.dump(knn, os.path.join(MODEL_DIR, "knn_model.pkl"))
    print("   -> Trained & Saved KNN (knn_model.pkl)")
    
    # 4. Train Random Forest
    rf = RandomForestClassifier(n_estimators=10, random_state=42)
    rf.fit(X_all, y_all)
    joblib.dump(rf, os.path.join(MODEL_DIR, "rf_model.pkl"))
    print("   -> Trained & Saved Random Forest (rf_model.pkl)")
    
    # 5. Train MLP (Neural Network)
    mlp = MLPClassifier(hidden_layer_sizes=(10,), max_iter=500, random_state=42)
    mlp.fit(X_all, y_all)
    joblib.dump(mlp, os.path.join(MODEL_DIR, "mlp_model.pkl"))
    print("   -> Trained & Saved MLP (mlp_model.pkl)")
