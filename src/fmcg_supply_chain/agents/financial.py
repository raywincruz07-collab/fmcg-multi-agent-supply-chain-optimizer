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

        # Explicit terminology and assumptions
        demand_uplift_pct = scenario.get("demand_uplift_pct", 0.0)
        stockout_recovery_uplift_pct = scenario.get("stockout_recovery_uplift_pct", 0.0)
        pack_revenue_impact_pct = scenario.get("pack_revenue_impact_pct", 0.0)
        consolidation_multiplier = scenario.get("pack_consolidation_benefit_multiplier", 1.0)
        adopt_pack = scenario.get("adopt_pack_recommendations", False)

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

            # Financial Bridge: Baseline
            baseline_units = row["AvgDailyDemand"] * 365
            baseline_price = price
            baseline_revenue = baseline_units * baseline_price

            baseline_cogs = baseline_units * cost * cogs_ratio
            baseline_operating_overhead = baseline_revenue * overhead_ratio
            baseline_carrying_cost = row["AvgInventory"] * cost * carrying_cost_rate

            baseline_operating_contribution = (
                baseline_revenue
                - baseline_cogs
                - baseline_operating_overhead
                - baseline_carrying_cost
            )

            # Financial Bridge: Scenario
            # 1. Units affected by demand and stockout recovery
            scenario_units = (
                baseline_units * (1 + demand_uplift_pct) * (1 + stockout_recovery_uplift_pct)
            )

            # 2. Revenue affected by units and pack-related pricing impact
            scenario_revenue = scenario_units * baseline_price * (1 + pack_revenue_impact_pct)

            # 3. COGS affected by units and pack consolidation multiplier
            scenario_volume_cogs = scenario_units * cost * cogs_ratio
            scenario_cogs = scenario_volume_cogs * consolidation_multiplier

            # 4. Overhead affected by revenue
            scenario_operating_overhead = scenario_revenue * overhead_ratio

            # 5. Inventory Carrying Cost affected by new pack sizes (assuming cycle stock = PackQty / 2)
            if adopt_pack:
                scenario_carrying_cost = (row["RecommendedPackQty"] / 2) * cost * carrying_cost_rate
            else:
                scenario_carrying_cost = baseline_carrying_cost

            scenario_operating_contribution = (
                scenario_revenue
                - scenario_cogs
                - scenario_operating_overhead
                - scenario_carrying_cost
            )

            # Mathematical signed effects
            revenue_effect = scenario_revenue - baseline_revenue
            cogs_effect = baseline_cogs - scenario_volume_cogs
            pack_conversion_effect = scenario_volume_cogs - scenario_cogs
            overhead_effect = baseline_operating_overhead - scenario_operating_overhead
            carrying_cost_effect = baseline_carrying_cost - scenario_carrying_cost

            total_contribution_change = (
                revenue_effect
                + cogs_effect
                + carrying_cost_effect
                + pack_conversion_effect
                + overhead_effect
            )

            operating_contribution_change_pct = (
                (total_contribution_change / abs(baseline_operating_contribution) * 100)
                if baseline_operating_contribution != 0
                else 0
            )

            fin_records.append(
                {
                    "SkuId": sku,
                    "Baseline_Units": baseline_units,
                    "Baseline_Unit_Price": baseline_price,
                    "Baseline_Revenue": baseline_revenue,
                    "Demand_Uplift_Pct": demand_uplift_pct,
                    "Stockout_Recovery_Uplift_Pct": stockout_recovery_uplift_pct,
                    "Pack_Revenue_Impact_Pct": pack_revenue_impact_pct,
                    "Scenario_Units": scenario_units,
                    "Scenario_Revenue": scenario_revenue,
                    "Scenario_COGS": scenario_cogs,
                    "Scenario_Carrying_Cost": scenario_carrying_cost,
                    "Scenario_Operating_Overhead": scenario_operating_overhead,
                    "Baseline_Operating_Contribution": baseline_operating_contribution,
                    "Revenue_Effect": revenue_effect,
                    "COGS_Effect": cogs_effect,
                    "Carrying_Cost_Effect": carrying_cost_effect,
                    "Pack_Conversion_Effect": pack_conversion_effect,
                    "Overhead_Effect": overhead_effect,
                    "Scenario_Operating_Contribution": scenario_operating_contribution,
                    "Total_Contribution_Change": total_contribution_change,
                    "Operating_Contribution_Change_Pct": operating_contribution_change_pct,
                }
            )

        fin_df = pd.DataFrame(fin_records)
        result.dataframes["financial_table_df"] = fin_df

        total_baseline_rev = fin_df["Baseline_Revenue"].sum()
        total_scenario_rev = fin_df["Scenario_Revenue"].sum()
        total_baseline_oc = fin_df["Baseline_Operating_Contribution"].sum()
        total_scenario_oc = fin_df["Scenario_Operating_Contribution"].sum()

        rev_change_pct = (
            ((total_scenario_rev - total_baseline_rev) / total_baseline_rev * 100)
            if total_baseline_rev > 0
            else 0
        )
        oc_change_pct = (
            ((total_scenario_oc - total_baseline_oc) / abs(total_baseline_oc) * 100)
            if total_baseline_oc != 0
            else 0
        )

        result.metrics["Scenario"] = active_scenario_name
        result.metrics["Revenue_Change_Pct"] = round(rev_change_pct, 2)
        result.metrics["Operating_Contribution_Change_Pct"] = round(oc_change_pct, 2)

        result.rationale.append(
            f"Financial bridge calculated for '{active_scenario_name}' scenario using strict terminology. No arbitrary clamping."
        )
        state.log_trace(
            self.name,
            "Financial Simulation",
            f"Operating Contribution Change: {oc_change_pct:.2f}% under {active_scenario_name} scenario.",
        )
