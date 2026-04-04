import requests
import time
import random
import math

# URL of your running backend
URL = "http://127.0.0.1:5000/api/data"

print("IoT Sensor Simulator Started...")
print("Press Ctrl+C to stop.")

# Simulate a 24-hour cycle in seconds (for demo speed)
day_cycle = 0 

while True:
    try:
        # 1. Generate REALISTIC Patterns (Sine Wave for Temp)
        temp_base = 25 + (10 * math.sin(day_cycle)) # Fluctuates between 15C and 35C
        
        # Add a tiny bit of random noise (sensors are never perfect)
        temperature = round(temp_base + random.uniform(-0.5, 0.5), 2)
        humidity = round(50 + random.uniform(-2, 2), 2)

        # 2. Occasionally inject a "Malicious" Attack (for your AI to catch)
        if random.randint(1, 20) == 1: # 5% chance of attack
            print("⚠️ INJECTING MALICIOUS DATA!")
            temperature = 100.0 # Fire attack!
            humidity = 5.0

        # 3. Send to Backend
        # Rotate through a few sensors to demonstrate reputation system
        sensor_id = random.choice(["sensor_1", "sensor_2", "sensor_3"])
        payload = {"temperature": temperature, "humidity": humidity, "sensor_id": sensor_id}
        response = requests.post(URL, json=payload)
        
        # 4. Print Result
        if response.status_code == 200:
            data = response.json()
            status = data.get("trust_status", "Unknown")
            print(f"Sent: {temperature}°C | Backend Reply: {status}")
        
        day_cycle += 0.1
        time.sleep(2) # Wait 2 seconds
        
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)