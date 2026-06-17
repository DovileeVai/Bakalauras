"""Prepare a clean normal-operation dataset from raw device CSV files."""

from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
OUTPUT_DIR = Path("data/processed")
OUTPUT_FILE = OUTPUT_DIR / "normal_dataset.csv"

# Sensor readings are matched only if timestamps differ by at most 1.5 seconds
MERGE_TOLERANCE_MS = 1500

# Read one raw CSV file and prepare its timestamp column
def read_raw_csv(file_name):
    path = RAW_DIR / file_name

    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")

    df = pd.read_csv(path)

    df["timestamp_ms"] = pd.to_numeric(df["timestamp_ms"], errors="coerce")
    df = df.dropna(subset=["timestamp_ms"])
    df["timestamp_ms"] = df["timestamp_ms"].astype("int64")

    if "timestamp" in df.columns:
        df["timestamp"] = df["timestamp"].astype(str)

    return df.sort_values("timestamp_ms")

# Remove rows written when a sensor is stopped
def remove_sensor_shutdown_rows(df):
    if "sensor_alive" not in df.columns:
        return df

    sensor_alive = pd.to_numeric(df["sensor_alive"], errors="coerce")
    return df[(sensor_alive.isna()) | (sensor_alive != 0)].copy()

# Prepare one sensor file and keep only timestamp and selected value column
def prepare_sensor_csv(file_name, value_col):
    df = read_raw_csv(file_name)
    df = remove_sensor_shutdown_rows(df)

    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=[value_col])

    return df[["timestamp_ms", "timestamp", value_col]].sort_values("timestamp_ms")

# Prepare sprinkler state values for merging with sensor data
def prepare_sprinkler_csv():
    df = read_raw_csv("sprinkler.csv")

    df["watering"] = df["watering"].astype(str).str.strip().map({"True": True, "False": False})

    return df[["timestamp_ms", "watering"]].sort_values("timestamp_ms")

# Match another sensor reading to the closest timestamp in the base dataset
def merge_nearest(base, other, value_col):
    return pd.merge_asof(
        base.sort_values("timestamp_ms"),
        other[["timestamp_ms", value_col]].sort_values("timestamp_ms"),
        on="timestamp_ms",
        direction="nearest",
        tolerance=MERGE_TOLERANCE_MS,
    )

# Add the last known sprinkler state to each row
def add_watering_state(dataset, sprinkler):
    dataset = pd.merge_asof(
        dataset.sort_values("timestamp_ms"),
        sprinkler.sort_values("timestamp_ms"),
        on="timestamp_ms",
        direction="backward",
    )

    dataset["watering"] = dataset["watering"].fillna(False).astype(bool)

    return dataset

# Fix short mismatches between watering state and water flow
def fix_watering_flow_mismatches(dataset):
    dataset = dataset.copy()

    no_flow_while_watering = ((dataset["watering"] == True) & (dataset["water_flow"] <= 0))

    flow_while_not_watering = ((dataset["watering"] == False) & (dataset["water_flow"] > 0))

    dataset.loc[no_flow_while_watering, "watering"] = False
    dataset.loc[flow_while_not_watering, "watering"] = True

    return dataset

def main():
    temperature = prepare_sensor_csv("temperature_sensor.csv", "temperature")
    air_humidity = prepare_sensor_csv("air_humidity_sensor.csv", "air_humidity")
    soil_moisture = prepare_sensor_csv("soil_moisture_sensor.csv", "soil_moisture")
    water_flow = prepare_sensor_csv("water_flow_sensor.csv", "water_flow")
    sprinkler = prepare_sprinkler_csv()

    # Soil moisture is used as the main time axis
    dataset = soil_moisture.copy()

    # Add other sensror readings by nearest timestamp
    dataset = merge_nearest(dataset, temperature, "temperature")
    dataset = merge_nearest(dataset, air_humidity, "air_humidity")
    dataset = merge_nearest(dataset, water_flow, "water_flow")
    dataset = add_watering_state(dataset, sprinkler)

    dataset = fix_watering_flow_mismatches(dataset)

    dataset = dataset.dropna(subset=[
        "temperature",
        "air_humidity",
        "soil_moisture",
        "water_flow",
        "watering",
    ])

    dataset["watering"] = dataset["watering"].astype(int)

    final_columns = [
        "timestamp_ms",
        "timestamp",
        "temperature",
        "air_humidity",
        "soil_moisture",
        "water_flow",
        "watering",
    ]

    dataset = dataset[final_columns].sort_values("timestamp_ms")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(OUTPUT_FILE, index=False)

    print(f"Saved normal dataset to: {OUTPUT_FILE}")
    print(f"Final rows: {len(dataset)}")


if __name__ == "__main__":
    main()