"""Add time-based features for soil moisture."""

from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path("data/processed")
SOIL_MOISTURE_WINDOW_SIZE = 10

NORMAL_INPUT_FILE = PROCESSED_DIR / "normal_dataset.csv"
NORMAL_OUTPUT_FILE = PROCESSED_DIR / "normal_dataset_features.csv"

ANOMALY_INPUT_FILE = PROCESSED_DIR / "dataset_with_anomalies.csv"
ANOMALY_OUTPUT_FILE = PROCESSED_DIR / "dataset_with_anomalies_features.csv"

def add_soil_moisture_features(df):
    # Change from the previous measurement
    df["soil_moisture_change"] = df["soil_moisture"].diff()

    # Change over tjw last 10 measurements
    df["soil_moisture_change_10"] = df["soil_moisture"] - df["soil_moisture"].shift(SOIL_MOISTURE_WINDOW_SIZE)

    # Variation over the last 10 measurements
    df["soil_moisture_std_10"] = df["soil_moisture"].rolling(window=SOIL_MOISTURE_WINDOW_SIZE).std()

    feature_columns = [
        "soil_moisture_change",
        "soil_moisture_change_10",
        "soil_moisture_std_10",
    ]

    # First rows do not have enough previous measurements, so they are filled with 0
    df[feature_columns] = df[feature_columns].fillna(0)

    return df


def main():
    if not NORMAL_INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {NORMAL_INPUT_FILE}")
    
    normal_df = pd.read_csv(NORMAL_INPUT_FILE)
    normal_df = add_soil_moisture_features(normal_df)
    normal_df.to_csv(NORMAL_OUTPUT_FILE, index=False)

    print(f"Saved normal dataset with features to: {NORMAL_OUTPUT_FILE}")
    print(f"Rows: {len(normal_df)}")

    if not ANOMALY_INPUT_FILE.exists():
        raise FileNotFoundError(f"Mssing input file: {ANOMALY_INPUT_FILE}")

    anomaly_df = pd.read_csv(ANOMALY_INPUT_FILE)
    anomaly_df = add_soil_moisture_features(anomaly_df)
    anomaly_df.to_csv(ANOMALY_OUTPUT_FILE, index=False)

    print(f"Saved anomaly dataset with features to: {ANOMALY_OUTPUT_FILE}")
    print(f"Rows: {len(anomaly_df)}") 


if __name__ == "__main__":
    main()