"""Apply LOF anomaly detection method"""

from pyod.models.lof import LOF

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

# LOF neighbors values used for comparison
N_NEIGHBORS_VALUES = [5, 10, 20, 30, 40, 50, 75, 100]

def run_lof_experiment(train_df, test_df, features, experiment_name, n_neighbors):
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

    model = LOF(
        n_neighbors=n_neighbors,
        contamination=CONTAMINATION,
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

    prepared_test_df["lof_score"] = anomaly_scores
    prepared_test_df["lof_pred"] = y_pred

    safe_name = experiment_name.lower().replace(" ", "_").replace("+", "plus").replace("=", "")

    results_file = RESULTS_DIR / f"{safe_name}_results.csv"
    prepared_test_df.to_csv(results_file, index=False)

    summary = summarize_by_anomaly_type(
        prepared_test_df,
        prediction_column="lof_pred",
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

    best_k = 75

    for n_neighbors in N_NEIGHBORS_VALUES:
        run_lof_experiment(
            train_df=train_df,
            test_df=test_df,
            features=BASE_FEATURES,
            experiment_name=f"LOF base features k={n_neighbors}",
            n_neighbors=n_neighbors,
        )

    for n_neighbors in N_NEIGHBORS_VALUES:
        run_lof_experiment(
            train_df=train_df,
            test_df=test_df,
            features=ALL_FEATURES,
            experiment_name=f"LOF base plus derived features k={n_neighbors}",
            n_neighbors=n_neighbors,
        )

if __name__ == "__main__":
    main()