import pandas as pd
from fmcg_supply_chain.agents.base import BaseAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult


class PackSizeOptimizationAgent(BaseAgent):
    def __init__(self):
        super().__init__("Pack Size Optimization")

    def _run(self, state: PipelineState, result: AgentResult) -> None:
        cfg = state.config.get("pack_size", {})
        multipliers = cfg.get(
            "multipliers", {"fast_mover": 14, "medium_mover": 30, "slow_mover": 90}
        )
        moq = cfg.get("moq", 100)
        units_per_case = cfg.get("units_per_case", 12)

        # We need the forecast from Demand agent
        demand_res = state.agent_results.get("Demand Intelligence")
        if not demand_res or "forecast_df" not in demand_res.dataframes:
            result.status = "error"
            result.warnings.append("No demand forecast available. Cannot optimize pack sizes.")
            return

        forecast_df = demand_res.dataframes["forecast_df"]

        # Calculate daily mean forecast per SKU
        mean_forecast = forecast_df.groupby("SkuId")["ForecastQty"].mean().reset_index()
        mean_forecast.rename(columns={"ForecastQty": "MeanDailyDemand"}, inplace=True)

        # We classify velocity by terciles of demand for simplicity and robustness
        if len(mean_forecast) > 2:
            terciles = pd.qcut(
                mean_forecast["MeanDailyDemand"],
                3,
                labels=["slow_mover", "medium_mover", "fast_mover"],
                duplicates="drop",
            )
        else:
            terciles = ["medium_mover"] * len(mean_forecast)
        mean_forecast["VelocityClass"] = terciles

        recos = []

        for _, row in mean_forecast.iterrows():
            sku = row["SkuId"]
            demand = row["MeanDailyDemand"]
            v_class = row["VelocityClass"]

            # Domain logic: Recommended Pack = (Mean Daily Demand * coverage multiplier)
            coverage_days = multipliers.get(v_class, 30)
            raw_target = demand * coverage_days

            # Constraints: Must be multiple of units_per_case
            cases_needed = max(1, round(raw_target / units_per_case))
            rec_pack_qty = cases_needed * units_per_case

            # MOQ Constraint
            if rec_pack_qty < moq:
                rec_pack_qty = moq

            recos.append(
                {
                    "SkuId": sku,
                    "VelocityClass": v_class,
                    "MeanDailyDemand": round(demand, 2),
                    "CoverageDays": coverage_days,
                    "RawTarget": round(raw_target, 2),
                    "RecommendedPackQty": rec_pack_qty,
                    "CasesNeeded": int(rec_pack_qty / units_per_case),
                }
            )

            state.log_trace(
                self.name,
                f"Pack Size Recommendation ({sku})",
                f"Selected {rec_pack_qty} units because it satisfies MOQ {moq} and case multiple {units_per_case}.",
            )

        reco_df = pd.DataFrame(recos)
        result.dataframes["recommendations_df"] = reco_df

        # Summaries
        fast = len(reco_df[reco_df["VelocityClass"] == "fast_mover"])
        med = len(reco_df[reco_df["VelocityClass"] == "medium_mover"])
        slow = len(reco_df[reco_df["VelocityClass"] == "slow_mover"])

        result.metrics["fast_movers"] = fast
        result.metrics["medium_movers"] = med
        result.metrics["slow_movers"] = slow

        result.rationale.append(
            "Pack sizes calculated based on exact MOQ and unit-per-case multiples."
        )
        state.log_trace(self.name, "Velocity classified", f"Fast: {fast}, Med: {med}, Slow: {slow}")
