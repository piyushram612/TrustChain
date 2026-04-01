import kagglehub
import shutil
import os

# 1. Download the dataset
print(" Downloading dataset...")
path = kagglehub.dataset_download("divyansh22/intel-berkeley-research-lab-sensor-data")
print("✅ Download complete at:", path)

# 2. Find the .csv file in that folder
files = os.listdir(path)
csv_file = None
for f in files:
    if f.endswith('.csv') or f.endswith('.txt'):
        csv_file = os.path.join(path, f)
        break

# 3. Move it to your project folder
if csv_file:
    destination = "sensor_data.csv"
    shutil.copy(csv_file, destination)
    print(f" Success! File moved to your project folder as '{destination}'")
else:
    print(" Coudn't find a CSV/TXT file in the downloaded folder. Please check manually.")