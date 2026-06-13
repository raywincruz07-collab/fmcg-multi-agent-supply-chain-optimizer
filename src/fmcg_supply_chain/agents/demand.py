import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from fmcg_supply_chain.agents.base import BaseAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult


class DemandIntelligenceAgent(BaseAgent):
    def __init__(self):
        super().__init__("Demand Intelligence")

    def _wape(self, y_true, y_pred):
        sum_true = np.sum(y_true)
        if sum_true == 0:
            return 0.0
        return (np.sum(np.abs(y_true - y_pred)) / sum_true) * 100

    def _mae(self, y_true, y_pred):
        return np.mean(np.abs(y_true - y_pred))

    def _rmse(self, y_true, y_pred):
        return np.sqrt(np.mean((y_true - y_pred) ** 2))

    def _smape(self, y_true, y_pred):
        denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
        # Prevent division by zero
        mask = denom > 0
        smape = np.zeros_like(y_true, dtype=float)
        smape[mask] = np.abs(y_true[mask] - y_pred[mask]) / denom[mask]
        return np.mean(smape) * 100

    def _run(self, state: PipelineState, result: AgentResult) -> None:
        cfg = state.config.get("demand", {})
        val_days = cfg.get("validation_days", 30)
        test_days = cfg.get("test_days", 30)
        min_train_days = cfg.get("minimum_training_days", 90)
        total_req_days = val_days + test_days + min_train_days

        df = state.master_df.copy()
        df = df.sort_values(by=["SkuId", "Date"])

        skus = df["SkuId"].unique()

        forecast_records = []
        metrics_by_sku = []

        total_skus_forecasted = 0
        excluded_skus = 0

        for sku in skus:
            sku_df = df[df["SkuId"] == sku].copy()

            if len(sku_df) < total_req_days:
                result.rationale.append(
                    f"Skipping {sku}: insufficient data history (req: {total_req_days}, got: {len(sku_df)})."
                )
                excluded_skus += 1
                continue

            total_skus_forecasted += 1

            # Chronological splits
            test_start = len(sku_df) - test_days
            val_start = test_start - val_days

            train = sku_df.iloc[:val_start]
            val = sku_df.iloc[val_start:test_start]
            test = sku_df.iloc[test_start:]

            y_train = train["SalesOrderQty"].values
            y_val = val["SalesOrderQty"].values
            y_test = test["SalesOrderQty"].values

            # --- VALIDATION PHASE (Model Selection) ---
            # Baseline: Naive
            pred_naive_v = np.full(val_days, y_train[-1] if len(y_train) > 0 else 0)

            # Baseline: Rolling Mean
            rolling_7d = (
                np.mean(y_train[-7:])
                if len(y_train) >= 7
                else (np.mean(y_train) if len(y_train) > 0 else 0)
            )
            pred_rolling_v = np.full(val_days, rolling_7d)

            # Baseline: Seasonal Naive
            pred_seasonal_v = []
            if len(y_train) >= 7:
                last_7 = y_train[-7:]
                for i in range(val_days):
                    pred_seasonal_v.append(last_7[i % 7])
            else:
                pred_seasonal_v = pred_naive_v.copy()
            pred_seasonal_v = np.array(pred_seasonal_v)

            # Random Forest
            X_tr, Y_tr = [], []
            for i in range(7, len(y_train)):
                X_tr.append([y_train[i - 1], y_train[i - 7]])
                Y_tr.append(y_train[i])

            pred_rf_v = []
            if len(X_tr) > 5:
                rf = RandomForestRegressor(n_estimators=20, random_state=42)
                rf.fit(X_tr, Y_tr)
                curr_l1 = y_train[-1]
                curr_l7 = y_train[-7]
                hist = list(y_train[-7:])
                for step in range(val_days):
                    p = max(0, rf.predict([[curr_l1, curr_l7]])[0])
                    pred_rf_v.append(p)
                    hist.append(p)
                    curr_l1 = p
                    curr_l7 = hist[-7]
            else:
                pred_rf_v = pred_naive_v.tolist()
            pred_rf_v = np.array(pred_rf_v)

            # Evaluate Validation WAPE
            models_v = {
                "naive_last": self._wape(y_val, pred_naive_v),
                "rolling_mean_7d": self._wape(y_val, pred_rolling_v),
                "seasonal_naive_7d": self._wape(y_val, pred_seasonal_v),
                "random_forest": self._wape(y_val, pred_rf_v),
            }

            best_model_name = min(models_v, key=models_v.get)
            val_wape = models_v[best_model_name]

            competing_models = {k: v for k, v in models_v.items() if k != best_model_name}
            best_competing = (
                min(competing_models, key=competing_models.get) if competing_models else None
            )
            competing_wape = competing_models[best_competing] if best_competing else 0.0

            state.log_trace(
                self.name,
                f"Model Selection ({sku})",
                f"Selected {best_model_name} (WAPE: {val_wape:.1f}%) because validation WAPE was lower than {best_competing} (WAPE: {competing_wape:.1f}%).",
            )

            # --- TEST PHASE (Refit on Train+Val, Predict Test) ---
            # We combine train+val for final refit history
            y_refit = np.concatenate([y_train, y_val])

            if best_model_name == "naive_last":
                final_preds = np.full(test_days, y_refit[-1])
            elif best_model_name == "rolling_mean_7d":
                rm = np.mean(y_refit[-7:]) if len(y_refit) >= 7 else np.mean(y_refit)
                final_preds = np.full(test_days, rm)
            elif best_model_name == "seasonal_naive_7d":
                final_preds = []
                last_7 = y_refit[-7:] if len(y_refit) >= 7 else np.full(7, y_refit[-1])
                for i in range(test_days):
                    final_preds.append(last_7[i % 7])
                final_preds = np.array(final_preds)
            elif best_model_name == "random_forest":
                X_refit, Y_refit = [], []
                for i in range(7, len(y_refit)):
                    X_refit.append([y_refit[i - 1], y_refit[i - 7]])
                    Y_refit.append(y_refit[i])
                rf = RandomForestRegressor(n_estimators=20, random_state=42)
                rf.fit(X_refit, Y_refit)

                final_preds = []
                curr_l1 = y_refit[-1]
                curr_l7 = y_refit[-7]
                hist = list(y_refit[-7:])
                for step in range(test_days):
                    p = max(0, rf.predict([[curr_l1, curr_l7]])[0])
                    final_preds.append(p)
                    hist.append(p)
                    curr_l1 = p
                    curr_l7 = hist[-7]
                final_preds = np.array(final_preds)

            test_wape = self._wape(y_test, final_preds)
            test_mae = self._mae(y_test, final_preds)
            test_rmse = self._rmse(y_test, final_preds)
            test_smape = self._smape(y_test, final_preds)

            metrics_by_sku.append(
                {
                    "SkuId": sku,
                    "SelectedModel": best_model_name,
                    "Validation_WAPE": val_wape,
                    "Test_WAPE": test_wape,
                    "Test_MAE": test_mae,
                    "Test_RMSE": test_rmse,
                    "Test_sMAPE": test_smape,
                    "Train_Start": train["Date"].iloc[0],
                    "Train_End": train["Date"].iloc[-1],
                    "Val_Start": val["Date"].iloc[0],
                    "Val_End": val["Date"].iloc[-1],
                    "Test_Start": test["Date"].iloc[0],
                    "Test_End": test["Date"].iloc[-1],
                    "Test_Observation_Count": len(y_test),
                }
            )

            test_dates = test["Date"].values
            for i in range(test_days):
                forecast_records.append(
                    {
                        "Date": test_dates[i],
                        "SkuId": sku,
                        "ForecastQty": final_preds[i],
                        "SelectedModel": best_model_name,
                        "CI_Lower": max(0, final_preds[i] * 0.8),
                        "CI_Upper": final_preds[i] * 1.2,
                    }
                )

        forecast_df = pd.DataFrame(forecast_records)
        metrics_df = pd.DataFrame(metrics_by_sku)

        result.dataframes["forecast_df"] = forecast_df
        result.dataframes["metrics_df"] = metrics_df

        if len(metrics_df) > 0:
            avg_test_wape = metrics_df["Test_WAPE"].mean()
            rf_wins = len(metrics_df[metrics_df["SelectedModel"] == "random_forest"])

            result.metrics["Global_Test_WAPE"] = round(avg_test_wape, 2)
            result.metrics["Global_Test_MAE"] = round(metrics_df["Test_MAE"].mean(), 2)
            result.metrics["SKUs_Forecasted"] = total_skus_forecasted
            result.metrics["Excluded_SKUs"] = excluded_skus
            result.metrics["RF_Win_Rate"] = round((rf_wins / total_skus_forecasted) * 100, 1)

            result.rationale.append(
                f"Selected best model per SKU using validation WAPE. RF won {rf_wins} times. Excluded {excluded_skus} SKUs due to insufficient history."
            )
        else:
            result.warnings.append("No SKUs had enough history to forecast.")
            result.metrics["Excluded_SKUs"] = excluded_skus

        state.log_trace(
            self.name,
            "Forecasting completed",
            f"Forecasted {total_skus_forecasted} SKUs. Excluded {excluded_skus}.",
        )
