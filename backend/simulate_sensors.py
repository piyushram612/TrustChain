import requests
import time
import random

# --- ENDPOINTS ---
BACKEND_URL   = "http://127.0.0.1:5000/api/data"
REAL_DATA_URL = "http://127.0.0.1:5000/api/get_simulation_data"

SENSOR_IDS = ["sensor_1", "sensor_2", "sensor_3", "sensor_4", "sensor_5"]

print("=" * 55)
print("  IoT Sensor Simulator — Intel Lab Dataset Edition")
print("  Fetching real readings from backend stream...")
print("  Press Ctrl+C to stop.")
print("=" * 55)

while True:
    try:
        # ----------------------------------------------------------------
        # 1. Fetch the next real data point from the Intel dataset stream
        # ----------------------------------------------------------------
        try:
            raw = requests.get(REAL_DATA_URL, timeout=3).json()
            temperature = float(raw.get("temperature", 24.5))
            humidity    = float(raw.get("humidity",    45.0))
            label       = int(raw.get("label", 1))   # 0=malicious, 1=trusted (from 3-sigma)
            source      = "Intel"
        except Exception:
            # Fallback: synthetic sine-wave data
            import math
            t = time.time()
            temperature = round(25 + 10 * math.sin(t / 60), 2)
            humidity    = round(50 + random.uniform(-2, 2), 2)
            label       = 1
            source      = "Synthetic"

        # ----------------------------------------------------------------
        # 2. Optional: override with a manual attack (5 % chance)
        #    This exercises the malicious-data injection feature.
        # ----------------------------------------------------------------
        if random.randint(1, 20) == 1:
            print("⚠️  INJECTING MALICIOUS DATA (manual override)!")
            temperature = round(random.uniform(90, 120), 2)
            humidity    = round(random.uniform(0, 8), 2)
            label       = 0

        # ----------------------------------------------------------------
        # 3. Pick a sensor ID and post to the blockchain backend
        # ----------------------------------------------------------------
        sensor_id = random.choice(SENSOR_IDS)
        payload = {
            "temperature": temperature,
            "humidity":    humidity,
            "sensor_id":   sensor_id,
        }

        response = requests.post(BACKEND_URL, json=payload, timeout=5)

        if response.status_code == 200:
            data   = response.json()
            status = data.get("trust_status", "Unknown")
            comp   = data.get("composite_score", 0)
            tag    = "✅" if "Trusted" in status else "🚨"
            print(
                f"{tag} [{source}] {sensor_id} | "
                f"T={temperature:.1f}°C  H={humidity:.1f}%  "
                f"→ {status}  (score={comp:.2f})"
            )
        else:
            print(f"[WARN] Backend returned HTTP {response.status_code}")

    except Exception as e:
        print(f"[ERROR] {e}")

    time.sleep(2)   # 2 second cadence — matches Streamlit refresh
