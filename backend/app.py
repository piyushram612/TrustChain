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
DATA_FILE = "sensor_data.csv" # Your downloaded Intel dataset

# --- REAL DATA GENERATOR LOGIC ---
# This function loads the CSV once and streams it line-by-line
def init_data_stream():
    try:
        print(f"📂 Loading Real Data from {DATA_FILE}...")
        
        # 1. Read CSV (Handle different delimiters just in case)
        # Intel data is sometimes space-separated, sometimes comma. 
        # We try comma first.
        try:
            df = pd.read_csv(DATA_FILE)
        except:
            # Fallback for space-separated files
            df = pd.read_csv(DATA_FILE, delimiter=' ')
            
        # 2. Clean Column Names (Normalize to lower case)
        df.columns = [c.lower().strip() for c in df.columns]
        
        print(f"✅ Loaded {len(df)} rows of Real-World Sensor Data!")

        # 3. Create Infinite Generator
        def generator():
            while True: # Loop forever (restart file when done)
                for index, row in df.iterrows():
                    try:
                        # Extract and ensure float type
                        # Adjust keys if your CSV headers are different
                        if 'temperature' in row:
                            t = float(row['temperature'])
                        elif 'temp' in row:
                             t = float(row['temp'])
                        else:
                             t = 24.5 # Default

                        if 'humidity' in row:
                            h = float(row['humidity'])
                        elif 'hum' in row:
                            h = float(row['hum'])
                        else:
                            h = 45.0 # Default
                            
                        yield {"temperature": t, "humidity": h}
                    except Exception:
                        continue # Skip bad rows
        return generator()

    except Exception as e:
        print(f"⚠️ Error loading CSV ({e}). Using Random Fallback mode.")
        import random
        def random_gen():
            while True:
                yield {
                    "temperature": round(random.uniform(20, 25), 2), 
                    "humidity": round(random.uniform(40, 50), 2)
                }
        return random_gen()

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
def assess_trust(temp, humidity):
    if model is None:
        if 0 < temp < 50 and 0 < humidity < 100:
            return "Trusted (Fallback)", 0.5
        return "Malicious (Fallback)", 0.5

    features = np.array([[temp, humidity]])
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

@app.route('/api/data', methods=['POST'])
def receive_sensor_data():
    data = request.json
    temp = data.get('temperature')
    hum = data.get('humidity')

    # 1. AI Assessment
    trust_status, confidence = assess_trust(temp, hum)
    
    # 2. Create the Data Record
    record = {
        'timestamp': str(datetime.datetime.now()), 
        'temperature': temp,
        'humidity': hum,
        'trust_status': trust_status,
        'confidence': confidence
    }

    # 3. Add to Blockchain
    new_block = iot_chain.add_data(record)
    block_hash = iot_chain.hash(new_block)
    save_to_db(record, block_hash)

    if "Trusted" in trust_status:
        print(f" AI Approved (Real Data)! Mined Block #{new_block['index']}")
    else:
        print(f" THREAT DETECTED! Recorded Malicious Block #{new_block['index']}")

    return jsonify(record)

@app.route('/api/blockchain', methods=['GET'])
def get_blockchain():
    return jsonify(iot_chain.chain)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)