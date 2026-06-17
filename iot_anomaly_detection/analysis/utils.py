from pathlib import Path

import pandas as pd

from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler

TRAIN_FILE = Path("data/processed/normal_dataset_features_2.csv")
TEST_FILE = Path("data/processed/dataset_with_anomalies_features_1.csv")

RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

BASE_FEATURES = [
    "temperature",
    "air_humidity",
    "soil_moisture",
    "water_flow",
    "watering",
]

ALL_FEATURES = [
    "temperature",
    "air_humidity",
    "soil_moisture",
    "water_flow",
    "watering",
    "soil_moisture_change",
    "soil_moisture_change_10",
    "soil_moisture_std_10",
]

FEATURE_SETS = {
    "P": BASE_FEATURES,
    "P + change": BASE_FEATURES + ["soil_moisture_change"],
    "P + change_10": BASE_FEATURES + ["soil_moisture_change_10"],
    "P + std_10": BASE_FEATURES + ["soil_moisture_std_10"],
    "P + change + change_10": BASE_FEATURES + ["soil_moisture_change", "soil_moisture_change_10"],
    "P + change + std_10": BASE_FEATURES + ["soil_moisture_change", "soil_moisture_std_10"],
    "P + change_10 + std_10": BASE_FEATURES + ["soil_moisture_change_10", "soil_moisture_std_10"],
    "P + I": ALL_FEATURES,
}

ROWS_TO_SKIP = 10

# Overall rows in anomalies dataset = 3565;
# minus first 10 fows: 3565 - 10 = 3555;
# 150 anomalies injected;
# contamination = 150 / 3555 = 0.042...
CONTAMINATION = 0.042
    
# Load training and testing datasets
def load_data():
    if not TRAIN_FILE.exists():
        raise FileNotFoundError(f"Train file: {TRAIN_FILE} not found")
    
    if not TEST_FILE.exists():
        raise FileNotFoundError(f"Test file: {TEST_FILE} not found")
    
    train_df = pd.read_csv(TRAIN_FILE)
    test_df = pd.read_csv(TEST_FILE)

    print("Datasets loaded.")
    print(f"Training rows: {len(train_df)}")
    print(f"Testing rows: {len(test_df)}")

    return train_df, test_df

# Prepare data for PyOD models
def prepare_data(train_df, test_df, features, use_scaling=True):
    train_df = train_df.iloc[ROWS_TO_SKIP:]
    test_df = test_df.iloc[ROWS_TO_SKIP:]

    X_train = train_df[features].to_numpy()
    X_test = test_df[features].to_numpy()
    y_true = test_df["is_anomaly"].astype(int)
    
    if use_scaling:
        scaler = StandardScaler()

        # Fit scaler only on normal training data
        X_train = scaler.fit_transform(X_train)

        # Use the same scaler for testing data
        X_test = scaler.transform(X_test)

    return X_train, X_test, y_true, test_df.copy()

# Calculate and print evaluation metrics
def evaluate_predictions(y_true, y_pred, title):
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    print()
    print("=" * 60)
    print(title)
    print("=" * 60)
   
    print(f"TP: {tp} | FP: {fp} | FN: {fn} | TN: {tn}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"F1-score:  {f1:.3f}")
    print(f"Predicted anomalies: {int(y_pred.sum())}")

# Summarize how many anomalies were detected for each anomaly type
def summarize_by_anomaly_type(test_df, prediction_column):
    summary = (
        test_df.groupby("anomaly_type")
        .agg(
            total=("is_anomaly", "count"),
            real_anomalies=("is_anomaly", "sum"),
            detected_as_anomaly=(prediction_column, "sum"),
        )
        .reset_index()
    )

    return summary