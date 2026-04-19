import sqlite3
import hashlib
import json
import datetime
import joblib
import numpy as np
import os
import pandas as pd # REQUIRED: pip install pandas
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
DB_NAME = "iot_project.db"
MODEL_FILE = "trust_model.pkl"
INTEL_DATA_FILE = "sensor_data.csv"       # Intel Lab IoT dataset (space-sep, no header)
FALLBACK_DATA_FILE = "sensor_dataset.csv" # Original small CSV fallback

INTEL_COLS = ['date', 'time', 'epoch', 'moteid',
               'temperature', 'humidity', 'light', 'voltage']
SENSOR_COLS = ['temperature', 'humidity', 'light', 'voltage']

# Populated during init — used by /api/status and Streamlit sidebar
dataset_info = {"source": "unknown", "rows": 0}

# --- REAL DATA GENERATOR LOGIC ---
# Loads the CSV once, preprocesses it, and streams it row-by-row
def init_data_stream():
    global dataset_info

    # ------------------------------------------------------------------ #
    #  Helper: load & preprocess Intel Lab dataset                         #
    # ------------------------------------------------------------------ #
    def _load_intel(path):
        df = pd.read_csv(path, sep=' ', header=None, names=INTEL_COLS,
                         on_bad_lines='skip')
        # Combine date + time → datetime
        df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'],
                                        errors='coerce')
        df.drop(columns=['date', 'time'], inplace=True)
        # Coerce sensor columns to numeric
        for col in SENSOR_COLS:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        # Drop NaN rows
        df.dropna(subset=SENSOR_COLS + ['datetime'], inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    # ------------------------------------------------------------------ #
    #  Helper: 3-sigma labeling                                            #
    # ------------------------------------------------------------------ #
    def _add_sigma_labels(df):
        means = df[SENSOR_COLS].mean()
        stds  = df[SENSOR_COLS].std()
        outlier_mask = ((df[SENSOR_COLS] - means).abs() > 3 * stds).any(axis=1)
        import numpy as _np
        df['label'] = _np.where(outlier_mask, 0, 1)
        return df

    # ------------------------------------------------------------------ #
    #  Decide which dataset to use                                         #
    # ------------------------------------------------------------------ #
    df = None
    using_intel = False

    intel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              '..', INTEL_DATA_FILE)
    intel_path = os.path.normpath(intel_path)

    if os.path.exists(intel_path):
        try:
            print(f"[INFO] Loading Intel Lab IoT Dataset from '{intel_path}'...")
            df = _load_intel(intel_path)
            df = _add_sigma_labels(df)
            if len(df) > 50000:
                print(f"[INFO] Sampling 50,000 rows (from {len(df)})...")
                df = df.sample(n=50000, random_state=42).reset_index(drop=True)
            using_intel = True
            dataset_info = {"source": f"Intel Lab IoT Dataset ({intel_path})",
                            "rows": len(df)}
            print(f"[OK] Intel dataset ready — {len(df)} rows.")
        except Exception as e:
            print(f"[WARNING] Intel dataset load failed ({e}). Falling back to '{FALLBACK_DATA_FILE}'.")
            df = None

    if df is None:
        # Fallback path: look relative to app.py
        fallback_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     '..', FALLBACK_DATA_FILE)
        fallback_path = os.path.normpath(fallback_path)
        try:
            print(f"[WARNING] Using fallback dataset: '{fallback_path}'")
            df = pd.read_csv(fallback_path)
            df.columns = [c.lower().strip() for c in df.columns]
            dataset_info = {"source": f"Fallback: {FALLBACK_DATA_FILE}",
                            "rows": len(df)}
            print(f"[OK] Fallback dataset ready — {len(df)} rows.")
        except Exception as e:
            print(f"[ERROR] Fallback dataset also failed ({e}). Using random generator.")
            import random
            def random_gen():
                while True:
                    yield {
                        "temperature": round(random.uniform(20, 25), 2),
                        "humidity":    round(random.uniform(40, 50), 2),
                        "light":       round(random.uniform(100, 400), 2),
                        "voltage":     round(random.uniform(2.4, 3.0), 2),
                        "label":       1
                    }
            dataset_info = {"source": "Random generator (both CSV files missing)", "rows": 0}
            return random_gen()

    print(f"[INFO] Dataset in use: {dataset_info['source']} ({dataset_info['rows']} rows)")

    # ------------------------------------------------------------------ #
    #  Build an infinite streaming generator from the dataframe            #
    # ------------------------------------------------------------------ #
    def generator():
        while True:  # Loop forever — restart when exhausted
            for _, row in df.iterrows():
                try:
                    t = float(row['temperature'])
                    h = float(row['humidity'])
                    # light / voltage only present in Intel dataset
                    l = float(row['light'])   if 'light'   in row and pd.notna(row['light'])   else 0.0
                    v = float(row['voltage']) if 'voltage' in row and pd.notna(row['voltage']) else 0.0
                    lbl = int(row['label'])   if 'label'   in row else 1
                    yield {"temperature": t, "humidity": h,
                           "light": l, "voltage": v, "label": lbl}
                except Exception:
                    continue
    return generator()

# Initialize the stream
data_stream = init_data_stream()


# --- MOBILE UI HTML (Updated for Real Data Fetching) ---
MOBILE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>IoT Sensor Auto-Pilot</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Rajdhani:wght@600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --neon-cyan: #00f3ff;
            --neon-red: #ff0055;
            --neon-purple: #bc13fe;
            --bg-dark: #050505;
            --card-bg: #111;
        }

        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

        body {
            font-family: 'JetBrains Mono', monospace;
            background-color: var(--bg-dark);
            color: #fff;
            margin: 0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            transition: background 0.2s;
        }

        /* HEADER */
        .header { margin-bottom: 20px; text-align: center; }
        .node-id { 
            font-family: 'Rajdhani', sans-serif; 
            font-size: 1.8rem; 
            letter-spacing: 2px;
            margin-bottom: 5px;
        }
        
        /* MODE TOGGLE */
        .mode-switch {
            display: flex;
            background: #222;
            border-radius: 30px;
            padding: 5px;
            margin-bottom: 30px;
            position: relative;
            cursor: pointer;
            border: 1px solid #333;
        }
        .mode-option {
            padding: 10px 25px;
            z-index: 2;
            font-weight: bold;
            font-size: 0.9rem;
            transition: color 0.3s;
        }
        .mode-slider {
            position: absolute;
            top: 5px; left: 5px;
            width: 50%; height: calc(100% - 10px);
            background: var(--neon-cyan);
            border-radius: 25px;
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 1;
        }
        .auto-active .mode-slider { transform: translateX(96%); background: var(--neon-purple); }
        .auto-active body { border: 2px solid var(--neon-purple); }

        /* SENSOR CARDS */
        .sensor-card {
            background: var(--card-bg);
            width: 100%; max-width: 400px;
            padding: 25px;
            border-radius: 16px;
            border: 1px solid #222;
            margin-bottom: 20px;
            position: relative;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }

        .sensor-value {
            font-size: 3rem;
            font-weight: 700;
            margin: 10px 0;
            text-shadow: 0 0 15px rgba(255,255,255,0.1);
        }

        /* CUSTOM SLIDERS */
        input[type=range] {
            width: 100%; height: 6px;
            background: #333; border-radius: 3px;
            outline: none; -webkit-appearance: none;
        }
        input[type=range]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 24px; height: 24px;
            border-radius: 50%;
            background: #fff;
            box-shadow: 0 0 15px currentColor;
            margin-top: -9px;
            transition: left 0.3s ease;
        }

        /* ATTACK BUTTON */
        .btn-attack {
            width: 100%; max-width: 400px;
            padding: 20px;
            border: 1px solid var(--neon-red);
            background: rgba(255, 0, 85, 0.1);
            color: var(--neon-red);
            font-family: 'Rajdhani', sans-serif;
            font-size: 1.2rem; font-weight: 700;
            letter-spacing: 1px; text-transform: uppercase;
            border-radius: 12px; cursor: pointer;
            margin-top: 10px;
            transition: all 0.1s;
        }
        .btn-attack:active { transform: scale(0.95); background: var(--neon-red); color: black; }

        /* PULSE ANIMATION */
        @keyframes pulse-green { 0% { box-shadow: 0 0 0 0 rgba(0, 255, 153, 0.7); } 70% { box-shadow: 0 0 0 20px rgba(0, 255, 153, 0); } 100% { box-shadow: 0 0 0 0 rgba(0, 255, 153, 0); } }
        @keyframes pulse-red { 0% { box-shadow: 0 0 0 0 rgba(255, 0, 85, 0.7); } 70% { box-shadow: 0 0 0 20px rgba(255, 0, 85, 0); } 100% { box-shadow: 0 0 0 0 rgba(255, 0, 85, 0); } }
        
        .pulse-g { animation: pulse-green 0.5s ease-out; }
        .pulse-r { animation: pulse-red 0.5s ease-out; }

    </style>
</head>
<body>

    <div class="header">
        <div class="node-id">NODE: XJ-920</div>
        <div style="color: #666; font-size: 0.8rem;">SECURE IOT GATEWAY</div>
        <div style="color: #444; font-size: 0.6rem; margin-top: 5px;">SOURCE: INTEL LAB DATASET</div>
    </div>

    <div class="mode-switch" id="modeSwitch" onclick="toggleAutoMode()">
        <div class="mode-slider"></div>
        <div class="mode-option" id="opt-manual" style="color: #000;">MANUAL</div>
        <div class="mode-option" id="opt-auto" style="color: #888;">REAL DATA</div>
    </div>

    <div class="sensor-card" style="border-top: 3px solid var(--neon-cyan);">
        <div style="color: var(--neon-cyan); font-size: 0.8rem; letter-spacing: 1px;">TEMP SENSOR</div>
        <div class="sensor-value" id="tempVal">25°C</div>
        <input type="range" min="0" max="120" value="25" id="tempSlider" style="color: var(--neon-cyan);" oninput="updateManual()">
    </div>

    <div class="sensor-card" style="border-top: 3px solid var(--neon-purple);">
        <div style="color: var(--neon-purple); font-size: 0.8rem; letter-spacing: 1px;">HUMIDITY</div>
        <div class="sensor-value" id="humVal">50%</div>
        <input type="range" min="0" max="100" value="50" id="humSlider" style="color: var(--neon-purple);" oninput="updateManual()">
    </div>

    <button class="btn-attack" onclick="manualAttack()">⚠️ FORCE ATTACK</button>
    
    <div id="status" style="margin-top: 20px; color: #555; font-size: 0.8rem;">READY TO TRANSMIT</div>

    <script>
        let isAuto = false;
        let autoInterval;

        function toggleAutoMode() {
            isAuto = !isAuto;
            const switchEl = document.getElementById('modeSwitch');
            
            if (isAuto) {
                switchEl.classList.add('auto-active');
                document.getElementById('opt-manual').style.color = '#888';
                document.getElementById('opt-auto').style.color = '#000';
                document.getElementById('status').innerText = "♻️ STREAMING REAL DATA...";
                document.getElementById('status').style.color = "var(--neon-purple)";
                startAutoPilot();
            } else {
                switchEl.classList.remove('auto-active');
                document.getElementById('opt-manual').style.color = '#000';
                document.getElementById('opt-auto').style.color = '#888';
                document.getElementById('status').innerText = "✋ MANUAL CONTROL";
                document.getElementById('status').style.color = "#555";
                stopAutoPilot();
            }
        }

        function startAutoPilot() {
            // Run this loop every 2 seconds
            autoInterval = setInterval(() => {
                
                // --- NEW LOGIC: FETCH REAL DATA INSTEAD OF RANDOM ---
                fetch('/api/get_simulation_data')
                    .then(res => res.json())
                    .then(data => {
                        const t = Math.round(data.temperature);
                        const h = Math.round(data.humidity);

                        // Visual Update
                        document.getElementById('tempSlider').value = t;
                        document.getElementById('humSlider').value = h;
                        updateDisplay(t, h);

                        // Send to Blockchain
                        sendData(t, h);
                    })
                    .catch(err => console.error("Data Fetch Error:", err));

            }, 2000);
        }

        function stopAutoPilot() {
            clearInterval(autoInterval);
        }

        function updateManual() {
            if(isAuto) return; 
            let t = document.getElementById('tempSlider').value;
            let h = document.getElementById('humSlider').value;
            updateDisplay(t, h);
            sendData(t, h);
        }

        function manualAttack() {
            if(isAuto) toggleAutoMode(); 
            // Attack Values
            const t = 110;
            const h = 5;
            
            document.getElementById('tempSlider').value = t;
            document.getElementById('humSlider').value = h;
            updateDisplay(t, h);
            sendData(t, h);
        }

        function updateDisplay(t, h) {
            document.getElementById('tempVal').innerText = t + "°C";
            document.getElementById('humVal').innerText = h + "%";
            
            const tVal = document.getElementById('tempVal');
            if(t > 80) tVal.style.color = "var(--neon-red)";
            else tVal.style.color = "#fff";
        }

        function sendData(t, h) {
            fetch('/api/data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ temperature: t, humidity: h })
            })
            .then(res => res.json())
            .then(data => {
                const card = document.querySelector('.sensor-card');
                if(data.trust_status.includes("Trusted")) {
                    card.classList.remove('pulse-r');
                    card.classList.add('pulse-g');
                    setTimeout(() => card.classList.remove('pulse-g'), 500);
                } else {
                    card.classList.remove('pulse-g');
                    card.classList.add('pulse-r');
                    setTimeout(() => card.classList.remove('pulse-r'), 500);
                }
            });
        }
    </script>
</body>
</html>
"""

# --- 1. LOAD ML MODEL ---
try:
    if os.path.exists(MODEL_FILE):
        model = joblib.load(MODEL_FILE)
        print(f"ML Model '{MODEL_FILE}' Loaded Successfully")
    else:
        print("Model not found! Please run 'python train_model.py' first.")
        model = None
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

# --- LOAD ENHANCEMENT MODELS ---
import trust_enhancements
trust_enhancements.load_extended_models()

# --- 2. DATABASE LAYER ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            temperature REAL,
            humidity REAL,
            trust_status TEXT,
            confidence REAL,
            block_hash TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(data, block_hash):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sensor_readings (timestamp, temperature, humidity, trust_status, confidence, block_hash)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data['timestamp'], data['temperature'], data['humidity'], 
          data['trust_status'], data['confidence'], block_hash))
    conn.commit()
    conn.close()

# --- 3. BLOCKCHAIN LAYER ---
class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_block(previous_hash='0', proof=100)

    def create_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': str(datetime.datetime.now()),
            'proof': proof,
            'previous_hash': previous_hash,
            'data': [] 
        }
        self.chain.append(block)
        return block

    def get_last_block(self):
        return self.chain[-1]

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def add_data(self, data):
        last_block = self.get_last_block()
        proof = last_block['proof'] + 1 
        previous_hash = self.hash(last_block)
        new_block = self.create_block(proof, previous_hash)
        new_block['data'] = data
        return new_block

iot_chain = Blockchain()
init_db()

# --- 4. INTELLIGENCE LAYER ---
def assess_trust(temp, humidity, light=0.0, voltage=0.0):
    if model is None:
        if 0 < temp < 50 and 0 < humidity < 100:
            return "Trusted (Fallback)", 0.5
        return "Malicious (Fallback)", 0.5

    # Build full 4-feature vector; slice to however many the model expects
    all_features = np.array([[temp, humidity, light, voltage]])
    n = model.n_features_in_
    features = all_features[:, :n]

    prediction = model.predict(features)[0]
    score = model.decision_function(features)[0]
    confidence = 0.5 + (min(max(score, -0.5), 0.5))

    if prediction == 1:
        return "Trusted", confidence
    else:
        return "Malicious", (1 - confidence)

# --- ROUTES ---
@app.route('/mobile')
def mobile_ui():
    return render_template_string(MOBILE_HTML)

# NEW ROUTE: Fetch Real Data from CSV
@app.route('/api/get_simulation_data', methods=['GET'])
def get_simulation_data():
    # Get next data point from the generator
    data = next(data_stream)
    return jsonify(data)

# NEW ROUTE: Dataset status — used by Streamlit sidebar warning
@app.route('/api/dataset_info', methods=['GET'])
def get_dataset_info():
    return jsonify(dataset_info)

@app.route('/api/data', methods=['POST'])
def receive_sensor_data():
    data = request.json
    temp      = float(data.get('temperature', 24.5))
    hum       = float(data.get('humidity',    45.0))
    light     = float(data.get('light',        0.0))
    voltage   = float(data.get('voltage',      0.0))
    sensor_id = data.get('sensor_id', 'sensor_1')

    # --- 1. Attack Simulation ---
    sim_data, is_attacked = trust_enhancements.simulate_attack(
        {'temperature': temp, 'humidity': hum}, probability=0.05
    )
    temp, hum = sim_data['temperature'], sim_data['humidity']

    # 2-feature slice for SVM/ensemble (trained on temp+humidity only)
    features_2 = np.array([[temp, hum]])

    # Base AI Assessment — uses 4-feature model automatically
    base_status, base_conf = assess_trust(temp, hum, light, voltage)

    # --- 2. Composite Score (SVM + Reputation) — still 2-feature ---
    composite_score = trust_enhancements.get_composite_trust_score(features_2, sensor_id, lambda_weight=0.5)
    
    # --- 3. Optional Ensemble Validation ---
    final_decision = None
    ensemble_triggered = False

    if 0.4 <= composite_score <= 0.6:
        ensemble_triggered = True
        ensemble_pred = trust_enhancements.trigger_ensemble_validation(features_2)
        final_decision = 1 if ensemble_pred == 1 else 0
        
        # Adjust composite score based on ensemble vote
        if final_decision == 1:
            composite_score = min(1.0, composite_score + 0.2)
            trust_status = "Trusted (Ensemble Verified)"
        else:
            composite_score = max(0.0, composite_score - 0.2)
            trust_status = "Malicious (Ensemble Rejected)"
    else:
        final_decision = 1 if composite_score >= 0.5 else 0
        trust_status = "Trusted" if final_decision == 1 else "Malicious"

    # --- 4. Reputation Update ---
    new_rep = trust_enhancements.update_reputation(sensor_id, final_decision)
    
    # --- 5. Explainability & Logging ---
    explanation = trust_enhancements.get_explanation()
    attack_str = "[ATTACK INJECTED]" if is_attacked else "[NORMAL]"
    
    print(f"\n{attack_str} Sensor: {sensor_id} | Final Decision: {trust_status}")
    print(f"   -> Composite Score: {composite_score:.2f} | Reputation: {new_rep:.2f}")
    if ensemble_triggered:
        print(f"   -> Ensemble Triggered. Explanation: {explanation}")

    confidence = composite_score if final_decision == 1 else (1 - composite_score)

    # 6. Create the Data Record (Blockchain accepts arbitrary JSON)
    record = {
        'timestamp': str(datetime.datetime.now()), 
        'temperature': temp,
        'humidity': hum,
        'trust_status': trust_status,
        'confidence': confidence,
        'sensor_id': sensor_id,
        'reputation': new_rep,
        'is_attacked': is_attacked,
        'composite_score': composite_score
    }

    # 7. Add to Blockchain
    new_block = iot_chain.add_data(record)
    block_hash = iot_chain.hash(new_block)
    save_to_db(record, block_hash)

    if "Trusted" in trust_status:
        print(f"[OK] AI Approved! Mined Block #{new_block['index']}")
    else:
        print(f"[ALERT] THREAT DETECTED! Recorded Malicious Block #{new_block['index']}")

    return jsonify(record)

@app.route('/api/blockchain', methods=['GET'])
def get_blockchain():
    return jsonify(iot_chain.chain)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)