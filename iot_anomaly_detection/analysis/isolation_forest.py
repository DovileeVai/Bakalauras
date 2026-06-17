"""Apply Isolation Forest anomaly detection method"""

from pyod.models.iforest import IForest

from analysis.utils import (
    RESULTS_DIR,
    BASE_FEATURES,
    ALL_FEATURES,
    FEATURE_SETS,
    CONTAMINATION,
    load_data,
    prepare_data,
    evaluate_predictions,
    summarize_by_anomaly_type,
)

RANDOM_STATE = 42

def run_iforest_experiment(train_df, test_df, features, experiment_name):
    print()
    print("#" * 80)
    print(f"Experiment: {experiment_name}")
    print("#" * 80)

    print("Used features:")
    for feature in features:
        print(f"- {feature}")

    X_train, X_test, y_true, prepared_test_df = prepare_data(
        train_df=train_df,
        test_df=test_df,
        features=features,
        use_scaling=True,
    )

    # n_estimators = 100 by default
    model = IForest(
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
    )

    # Train model on normal data
    model.fit(X_train)

    # PyOD returns 0 for normal rows and 1 for anomalies
    y_pred = model.predict(X_test)

    # Higher score means that a row is more anomalous
    anomaly_scores = model.decision_function(X_test)

    evaluate_predictions(
        y_true=y_true,
        y_pred=y_pred,
        title=experiment_name,
    )

    prepared_test_df["iforest_score"] = anomaly_scores
    prepared_test_df["iforest_pred"] = y_pred

    safe_name = experiment_name.lower().replace(" ", "_").replace("+", "plus").replace("=", "")

    results_file = RESULTS_DIR / f"{safe_name}_results.csv"
    prepared_test_df.to_csv(results_file, index=False)

    summary = summarize_by_anomaly_type(
        prepared_test_df,
        prediction_column="iforest_pred",
    )

    print()
    print("Detection by anomaly type:")
    print(summary)

    print()
    print(f"Results saved to: {results_file}")

def main():
    train_df, test_df = load_data()

    print()
    print("Anomaly counts in testing dataset:")
    print(test_df["anomaly_type"].value_counts())

    run_iforest_experiment(
        train_df=train_df,
        test_df=test_df,
        features=BASE_FEATURES,
        experiment_name="iForest base features",
    )

    run_iforest_experiment(
        train_df=train_df,
        test_df=test_df,
        features=ALL_FEATURES,
        experiment_name="iForest base plus derived features",
    )

if __name__ == "__main__":
    main()