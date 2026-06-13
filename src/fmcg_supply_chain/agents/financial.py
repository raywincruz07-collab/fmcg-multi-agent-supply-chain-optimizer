import pandas as pd
from fmcg_supply_chain.agents.base import BaseAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult


class FinancialImpactAgent(BaseAgent):
    def __init__(self):
        super().__init__("Financial Impact")

    def _run(self, state: PipelineState, result: AgentResult) -> None:
        fin_cfg = state.config.get("financial", {})
        active_scenario_name = state.config.get("active_scenario", "base")
        scenario = fin_cfg.get(active_scenario_name, {})

        cogs_ratio = scenario.get("cogs_ratio", 0.60)
        overhead_ratio = scenario.get("overhead_ratio", 0.12)
        carrying_cost_rate = scenario.get("carrying_cost_rate", 0.20)
        demand_uplift_pct = scenario.get("demand_uplift_pct", 0.05)
        consolidation_multiplier = scenario.get("pack_consolidation_benefit_multiplier", 0.90)

        # We need historical master_df to calculate current "Before"
        # We need pack recommendations to calculate "After"
        master_df = state.master_df
        pack_res = state.agent_results.get("Pack Size Optimization")

        if not pack_res or "recommendations_df" not in pack_res.dataframes:
            result.status = "error"
            result.warnings.append("No pack recommendations available.")
            return

        reco_df = pack_res.dataframes["recommendations_df"]

        # Historical aggregates
        hist_agg = (
            master_df.groupby("SkuId")
            .agg(
                AvgPrice=("Price", "mean"),
                AvgCost=("UnitCost", "mean"),
                AvgDailyDemand=("SalesOrderQty", "mean"),
                AvgInventory=("OnHandQty", "mean"),
            )
            .reset_index()
        )

        merged = hist_agg.merge(reco_df, on="SkuId", how="inner")

        fin_records = []
        for _, row in merged.iterrows():
            sku = row["SkuId"]
            price = row["AvgPrice"]
            cost = row["AvgCost"]

            # BEFORE calculations (daily annualized for simplicity: * 365)
            before_demand_yr = row["AvgDailyDemand"] * 365
            before_revenue = before_demand_yr * price
            before_cogs = before_demand_yr * cost * cogs_ratio
            before_overhead = before_revenue * overhead_ratio
            before_inv_cost = row["AvgInventory"] * cost * carrying_cost_rate
            before_pbt = before_revenue - before_cogs - before_overhead - before_inv_cost

            # AFTER calculations based on scenarios (NO target clamping)
            # Uplift in demand from better pack sizing
            after_demand_yr = before_demand_yr * (1 + demand_uplift_pct)
            after_revenue = after_demand_yr * price

            # Cost savings from consolidation
            after_cogs = (after_demand_yr * cost * cogs_ratio) * consolidation_multiplier
            after_overhead = after_revenue * overhead_ratio

            # Inventory reduction assumption based on strictly larger pack coverage reducing frequency
            # (Rough assumption: new average inventory is half the recommended pack qty)
            new_avg_inv = row["RecommendedPackQty"] / 2
            after_inv_cost = new_avg_inv * cost * carrying_cost_rate

            after_pbt = after_revenue - after_cogs - after_overhead - after_inv_cost

            # Calculate explicit changes
            pbt_change = after_pbt - before_pbt
            pbt_uplift_pct = (pbt_change / abs(before_pbt) * 100) if before_pbt != 0 else 0

            fin_records.append(
                {
                    "SkuId": sku,
                    "Before_Revenue": before_revenue,
                    "Before_PBT": before_pbt,
                    "After_Revenue": after_revenue,
                    "After_PBT": after_pbt,
                    "PBT_Uplift_Pct": pbt_uplift_pct,
                }
            )

        fin_df = pd.DataFrame(fin_records)
        result.dataframes["financial_table_df"] = fin_df

        total_before_rev = fin_df["Before_Revenue"].sum()
        total_after_rev = fin_df["After_Revenue"].sum()
        total_before_pbt = fin_df["Before_PBT"].sum()
        total_after_pbt = fin_df["After_PBT"].sum()

        rev_uplift_pct = (
            ((total_after_rev - total_before_rev) / total_before_rev * 100)
            if total_before_rev > 0
            else 0
        )
        pbt_uplift_pct = (
            ((total_after_pbt - total_before_pbt) / abs(total_before_pbt) * 100)
            if total_before_pbt != 0
            else 0
        )

        result.metrics["Scenario"] = active_scenario_name
        result.metrics["Revenue_Uplift_Pct"] = round(rev_uplift_pct, 2)
        result.metrics["PBT_Uplift_Pct"] = round(pbt_uplift_pct, 2)

        result.rationale.append(
            f"Financials calculated under '{active_scenario_name}' scenario assumptions without target clamping."
        )
        state.log_trace(
            self.name,
            "Financial Simulation",
            f"PBT Uplift: {pbt_uplift_pct:.2f}% under {active_scenario_name} scenario.",
        )
