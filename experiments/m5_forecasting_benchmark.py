import os
import sys
from pathlib import Path
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error


def wape(y_true, y_pred):
    return (abs(y_true - y_pred).sum() / y_true.sum()) * 100 if y_true.sum() > 0 else 0


def run_m5_benchmark():
    print("================================================================")
    print("          M5 Forecasting Dataset Benchmark (Standalone)         ")
    print("================================================================")

    root = Path(__file__).resolve().parent.parent
    m5_dir = root / "data" / "raw" / "m5"

    cal_path = m5_dir / "calendar.csv"
    sales_path = m5_dir / "sales_train_validation.csv"

    if not cal_path.exists() or not sales_path.exists():
        print("[INFO] M5 dataset not found in data/raw/m5/. Skipping benchmark.")
        print("[INFO] This benchmark is completely independent of the main SupplyGraph pipeline.")
        sys.exit(0)

    print("Loading M5 data...")
    cal = pd.read_csv(cal_path)
    sales = pd.read_csv(sales_path)

    # We take just a tiny subset to prove the benchmark concept
    subset_sales = sales.head(10).copy()

    print(f"Running benchmark on {len(subset_sales)} sample M5 SKUs...")

    # Simple naive vs RF on the last 28 days
    # M5 columns are d_1 to d_1913
    d_cols = [c for c in subset_sales.columns if c.startswith("d_")]

    train_cols = d_cols[:-28]
    test_cols = d_cols[-28:]

    print("Evaluating Last-Value Naive vs Random Forest...")

    results = []

    for _, row in subset_sales.iterrows():
        item_id = row["item_id"]
        train_data = row[train_cols].values.astype(float)
        test_data = row[test_cols].values.astype(float)

        if len(train_data) == 0:
            continue

        # Naive Last
        last_val = train_data[-1]
        naive_preds = [last_val] * 28
        naive_wape = wape(test_data, naive_preds)

        # Simple RF (Lag 1)
        X_train, y_train = [], []
        for i in range(1, len(train_data)):
            X_train.append([train_data[i - 1]])
            y_train.append(train_data[i])

        if len(X_train) < 10:
            continue

        rf = RandomForestRegressor(n_estimators=10, random_state=42)
        rf.fit(X_train, y_train)

        rf_preds = []
        curr_x = train_data[-1]
        for _ in range(28):
            p = rf.predict([[curr_x]])[0]
            rf_preds.append(p)
            curr_x = p

        rf_wape = wape(test_data, rf_preds)

        results.append({"item_id": item_id, "Naive_WAPE": naive_wape, "RF_WAPE": rf_wape})

    res_df = pd.DataFrame(results)
    print("\nBenchmark Results (WAPE %):")
    print(res_df.mean())

    print(
        "\nConclusion: The Random Forest model should only be selected if it beats the Naive baseline."
    )
    print(
        "In this standalone M5 benchmark, we maintain strict chronological evaluation without data leakage."
    )


if __name__ == "__main__":
    run_m5_benchmark()
