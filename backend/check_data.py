import pandas as pd

# Load the first 5 rows
df = pd.read_csv('sensor_data.csv')
print("--- COLUMNS ---")
print(df.columns)
print("\n--- FIRST 5 ROWS ---")
print(df.head())