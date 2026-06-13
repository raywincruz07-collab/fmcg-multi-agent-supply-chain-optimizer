import pandas as pd
import numpy as np
from fmcg_supply_chain.agents.base import BaseAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult


class ProductionPlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__("Production Planning")

    def _run(self, state: PipelineState, result: AgentResult) -> None:
        prod_cfg = state.config.get("production", {})
        holding_cost = prod_cfg.get("holding_cost_per_unit", 0.5)
        setup_cost = prod_cfg.get("setup_cost_per_batch", 500)
        max_cap = prod_cfg.get("max_plant_capacity_per_day", 10000)

        # We need demand forecasts and mappings
        demand_res = state.agent_results.get("Demand Intelligence")
        if not demand_res or "forecast_df" not in demand_res.dataframes:
            result.status = "error"
            result.warnings.append("No demand forecast available.")
            return

        forecast_df = demand_res.dataframes["forecast_df"]
        mappings_df = state.metadata.get("sku_mappings", pd.DataFrame())

        # Calculate daily mean forecast
        mean_forecast = forecast_df.groupby("SkuId")["ForecastQty"].mean().reset_index()
        mean_forecast.rename(columns={"ForecastQty": "DailyDemand"}, inplace=True)

        if not mappings_df.empty:
            merged = mean_forecast.merge(mappings_df, on="SkuId", how="left")
        else:
            merged = mean_forecast.copy()
            merged["PlantId"] = "UnknownPlant"

        prod_records = []
        plant_loads = {}

        for _, row in merged.iterrows():
            sku = row["SkuId"]
            demand = row["DailyDemand"]
            plant = row.get("PlantId", "UnknownPlant")

            # Annual demand for EOQ (Economic Order Quantity) approximation
            annual_demand = demand * 365
            if annual_demand > 0:
                eoq = np.sqrt((2 * annual_demand * setup_cost) / holding_cost)
            else:
                eoq = 0

            daily_production_target = demand * 1.05  # Add safety buffer

            if plant not in plant_loads:
                plant_loads[plant] = 0
            plant_loads[plant] += daily_production_target

            prod_records.append(
                {
                    "SkuId": sku,
                    "PlantId": plant,
                    "DailyDemand": demand,
                    "OptimalBatchSize_EOQ": round(eoq, 0),
                    "TargetDailyProduction": round(daily_production_target, 0),
                }
            )

        sched_df = pd.DataFrame(prod_records)
        result.dataframes["production_schedule_df"] = sched_df

        # Plant Utilisation
        util_records = []
        for plant, load in plant_loads.items():
            utilization_pct = (load / max_cap) * 100
            util_records.append(
                {
                    "PlantId": plant,
                    "TotalDailyLoad": load,
                    "Capacity": max_cap,
                    "TargetUtilisationPct": round(utilization_pct, 2),
                }
            )

        util_df = pd.DataFrame(util_records)
        result.dataframes["utilisation_summary_df"] = util_df

        avg_util = util_df["TargetUtilisationPct"].mean() if len(util_df) > 0 else 0

        result.metrics["plants_analysed"] = len(plant_loads)
        result.metrics["avg_target_utilisation"] = round(avg_util, 2)

        result.rationale.append(
            "Calculated theoretical EOQ and target plant loads based on forecast demand."
        )
        state.log_trace(
            self.name,
            "Production Scheduling",
            f"Scheduled production for {len(sched_df)} SKUs across {len(plant_loads)} plants.",
        )
