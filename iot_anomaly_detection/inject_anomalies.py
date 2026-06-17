"""Injects controlled anomalies into the normal dataset"""

from pathlib import Path

import numpy as np
import pandas as pd

INPUT_FILE = Path("data/processed/normal_dataset.csv")
OUTPUT_FILE = Path("data/processed/dataset_with_anomalies.csv")

RANDOM_SEED = 42

# Number of rows used for each anomaly type
NO_FLOW_LENGTH = 25
FLOW_WHILE_OFF_LENGTH = 35
STUCK_SENSOR_LENGTH = 60
NO_SOIL_RESPONSE_LENGTH = 25
TEMPERATURE_SPIKE_LENGTH = 1

# 5 rows in the dataset where temperature spike anomaly is inserted
TEMPERATURE_SPIKE_POSITIONS = [0.55, 0.60, 0.65, 0.70, 0.75]

TEMPERATURE_SPIKE_VALUE = 60.0

# Find a continuous row range where an anomaly can be inserted (condition is True and no anomaly is already marked)
# start_from is a dataset position from 0 to 1 (0.30 is 30%)
def find_anomaly_range(df, condition, length, start_from=0.0):
    start_row = int(len(df) * start_from)
    last_start_row = len(df) - length

    available_rows = condition & (df["is_anomaly"] == 0)
    search_starts = list(range(start_row, last_start_row + 1)) + list(range(0, start_row))

    for start in search_starts:
        end = start + length

        if available_rows.iloc[start:end].all():
            return start, end

    raise ValueError("Could not find a suitable row range for anomaly injection.")

# Mark selected rows as anomalies
def mark_anomaly(df, start, end, anomaly_type):
    df.loc[start:end - 1, "is_anomaly"] = 1
    df.loc[start:end - 1, "anomaly_type"] = anomaly_type

# Insert anomaly: sprinkler is active, but water flow is zero
def inject_no_flow_while_watering(df):
    condition = df["watering"] == 1
    start, end = find_anomaly_range(df, condition, length=NO_FLOW_LENGTH, start_from=0.15)

    df.loc[start:end - 1, "water_flow"] = 0.0
    mark_anomaly(df, start, end, "no_flow_while_watering")

# Insert anomaly: water flow is detected while sprinkler is off
def inject_flow_while_not_watering(df, rng):
    condition = df["watering"] == 0
    start, end = find_anomaly_range(df, condition, length=FLOW_WHILE_OFF_LENGTH, start_from=0.30)

    df.loc[start:end - 1, "water_flow"] = np.round(rng.uniform(1.5, 2.5, end-start), 2)

    mark_anomaly(df, start, end, "flow_while_not_watering")

# Insert anomaly: soil moisture sensor sends the same value for a longer period
def inject_stuck_soil_moisture_sensor(df):
    condition = df["watering"] == 0
    start, end = find_anomaly_range(df, condition, length=STUCK_SENSOR_LENGTH, start_from=0.45)

    stuck_value = df.loc[start, "soil_moisture"]
    df.loc[start:end - 1, "soil_moisture"] = stuck_value

    mark_anomaly(df, start, end, "stuck_soil_moisture_sensor")

# Insert anomaly: short sudden temperature spikes
def inject_temperature_spike(df):
    condition = df["is_anomaly"] == 0

    for start_from in TEMPERATURE_SPIKE_POSITIONS:
        start, end = find_anomaly_range(df, condition, length=TEMPERATURE_SPIKE_LENGTH, start_from=start_from)

        df.loc[start:end - 1, "temperature"] = TEMPERATURE_SPIKE_VALUE
        mark_anomaly(df, start, end, "temperature_spike")

# Insert anomaly: sprinkler is on, water_flow > 0, but soil moisture does not increase
def inject_watering_without_soil_response(df):
    condition = (df["watering"] == 1) & (df["water_flow"] > 0)
    start, end = find_anomaly_range(df, condition, length=NO_SOIL_RESPONSE_LENGTH, start_from=0.80)

    start_value = df.loc[start, "soil_moisture"]

    df.loc[start:end - 1, "soil_moisture"] = np.round(start_value - np.linspace(0, 0.8, end - start), 2)

    mark_anomaly(df, start, end, "watering_without_soil_response")

def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_FILE}")
    
    rng = np.random.default_rng(RANDOM_SEED)

    df = pd.read_csv(INPUT_FILE)

    df["is_anomaly"] = 0
    df["anomaly_type"] = "normal"

    inject_no_flow_while_watering(df)
    inject_flow_while_not_watering(df, rng)
    inject_stuck_soil_moisture_sensor(df)
    inject_temperature_spike(df)
    inject_watering_without_soil_response(df)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"Saved dataset with anomalies to: {OUTPUT_FILE}")
    print(f"Rows: {len(df)}")
    print(f"Anomalies: {df['is_anomaly'].sum()}")

    print("\nAnomaly counts:")
    print(df["anomaly_type"].value_counts())

if __name__ == "__main__":
    main()