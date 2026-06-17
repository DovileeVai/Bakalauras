"""Check dataset with anomalies"""

from pathlib import Path

import pandas as pd

INPUT_FILE = Path("data/processed/dataset_with_anomalies.csv")

FEATURE_COLUMNS = [
    "temperature",
    "air_humidity",
    "soil_moisture",
    "water_flow",
    "watering",
    "is_anomaly",
]

def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_FILE}")
    
    df = pd.read_csv(INPUT_FILE)

    print("Rows:", len(df))
    print("Anomalies:", df["is_anomaly"].sum())

    print("\nAnomaly counts:")
    print(df["anomaly_type"].value_counts())

    print("\nMissing values:")
    print(df.isna().sum())

    print("\nValue ranges:")
    print(df[FEATURE_COLUMNS].agg(["min", "max"]))

    print("\nLogical checks:")

    no_flow_while_watering = ((df["watering"] == 1) & (df["water_flow"] <= 0))
    flow_while_not_watering = ((df["watering"] == 0) & (df["water_flow"] > 0))

    print("watering=1 and water_flow<=0:", no_flow_while_watering.sum())
    print("watering=0 and water_flow>0:", flow_while_not_watering.sum())

if __name__ == "__main__":
    main()