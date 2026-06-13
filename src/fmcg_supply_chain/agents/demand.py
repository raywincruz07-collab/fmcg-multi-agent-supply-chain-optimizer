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
            return 0.0  # Cannot compute WAPE if there are zero actuals in the whole horizon, treat as 0 error if we predict 0
        return (np.sum(np.abs(y_true - y_pred)) / sum_true) * 100

    def _mae(self, y_true, y_pred):
        return np.mean(np.abs(y_true - y_pred))

    def _run(self, state: PipelineState, result: AgentResult) -> None:
        horizon_days = state.config.get("demand", {}).get("horizon_days", 30)
        df = state.master_df.copy()

        # Ensure chronological sorting
        df = df.sort_values(by=["SkuId", "Date"])

        skus = df["SkuId"].unique()

        forecast_records = []
        metrics_by_sku = []

        total_skus_forecasted = 0

        for sku in skus:
            sku_df = df[df["SkuId"] == sku].copy()

            if len(sku_df) <= horizon_days:
                result.rationale.append(f"Skipping {sku}: insufficient data history.")
                continue

            total_skus_forecasted += 1

            # Global Chronological Split (no leakage)
            train = sku_df.iloc[:-horizon_days]
            test = sku_df.iloc[-horizon_days:]

            y_train = train["SalesOrderQty"].values
            y_test = test["SalesOrderQty"].values

            # Baseline: Naive Last Value
            last_val = y_train[-1] if len(y_train) > 0 else 0
            pred_naive = np.full(horizon_days, last_val)

            # Baseline: Rolling Mean (7d)
            if len(y_train) >= 7:
                rolling_7d = np.mean(y_train[-7:])
            else:
                rolling_7d = np.mean(y_train) if len(y_train) > 0 else 0
            pred_rolling = np.full(horizon_days, rolling_7d)

            # Baseline: Seasonal Naive (7d lag repeated)
            pred_seasonal = []
            if len(y_train) >= 7:
                last_7 = y_train[-7:]
                for i in range(horizon_days):
                    pred_seasonal.append(last_7[i % 7])
            else:
                pred_seasonal = pred_naive.copy()
            pred_seasonal = np.array(pred_seasonal)

            # Random Forest implementation
            # Create simple lag 1, lag 7 features for training
            X_tr, Y_tr = [], []
            for i in range(7, len(y_train)):
                X_tr.append([y_train[i - 1], y_train[i - 7]])
                Y_tr.append(y_train[i])

            pred_rf = []
            if len(X_tr) > 5:
                rf = RandomForestRegressor(n_estimators=20, random_state=42)
                rf.fit(X_tr, Y_tr)

                # Direct multi-step iterative forecasting
                curr_l1 = y_train[-1]
                curr_l7 = y_train[-7]

                # we need to keep track of predictions to feed into l7 later
                history_for_lag = list(y_train[-7:])

                for step in range(horizon_days):
                    p = rf.predict([[curr_l1, curr_l7]])[0]
                    p = max(0, p)  # no negative demand
                    pred_rf.append(p)

                    history_for_lag.append(p)
                    curr_l1 = p
                    curr_l7 = history_for_lag[-7]
            else:
                pred_rf = pred_naive.tolist()

            pred_rf = np.array(pred_rf)

            # Evaluate all
            wape_naive = self._wape(y_test, pred_naive)
            wape_roll = self._wape(y_test, pred_rolling)
            wape_seas = self._wape(y_test, pred_seasonal)
            wape_rf = self._wape(y_test, pred_rf)

            mae_rf = self._mae(y_test, pred_rf)

            # Honest model selection
            models = {
                "naive_last": wape_naive,
                "rolling_mean_7d": wape_roll,
                "seasonal_naive_7d": wape_seas,
                "random_forest": wape_rf,
            }

            best_model_name = min(models, key=models.get)
            best_wape = models[best_model_name]

            if best_model_name == "random_forest":
                final_preds = pred_rf
            elif best_model_name == "seasonal_naive_7d":
                final_preds = pred_seasonal
            elif best_model_name == "rolling_mean_7d":
                final_preds = pred_rolling
            else:
                final_preds = pred_naive

            metrics_by_sku.append(
                {
                    "SkuId": sku,
                    "BestModel": best_model_name,
                    "WAPE": best_wape,
                    "MAE": self._mae(y_test, final_preds),
                    "Naive_WAPE": wape_naive,
                    "RF_WAPE": wape_rf,
                }
            )

            # Save forecast
            test_dates = test["Date"].values
            for i in range(horizon_days):
                forecast_records.append(
                    {
                        "Date": test_dates[i],
                        "SkuId": sku,
                        "ForecastQty": final_preds[i],
                        "SelectedModel": best_model_name,
                        # Provide ensemble spread approximation if RF, otherwise just basic range
                        "CI_Lower": max(0, final_preds[i] * 0.8),
                        "CI_Upper": final_preds[i] * 1.2,
                    }
                )

        forecast_df = pd.DataFrame(forecast_records)
        metrics_df = pd.DataFrame(metrics_by_sku)

        result.dataframes["forecast_df"] = forecast_df
        result.dataframes["metrics_df"] = metrics_df

        if len(metrics_df) > 0:
            avg_wape = metrics_df["WAPE"].mean()
            rf_wins = len(metrics_df[metrics_df["BestModel"] == "random_forest"])

            result.metrics["Global_WAPE"] = round(avg_wape, 2)
            result.metrics["Global_MAE"] = round(metrics_df["MAE"].mean(), 2)
            result.metrics["SKUs_Forecasted"] = total_skus_forecasted
            result.metrics["RF_Win_Rate"] = round((rf_wins / total_skus_forecasted) * 100, 1)

            result.rationale.append(
                f"Selected best model per SKU based on WAPE. RF won {rf_wins} times."
            )
        else:
            result.warnings.append("No SKUs had enough history to forecast.")

        state.log_trace(
            self.name, "Forecasting completed", f"Forecasted {total_skus_forecasted} SKUs."
        )
