import pandas as pd
from fmcg_supply_chain.agents.financial import FinancialImpactAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult


def test_financial_neutral_scenario():
    """A neutral scenario must result in Scenario == Baseline for units and revenue."""
    agent = FinancialImpactAgent()

    # Setup state with neutral config
    config = {
        "active_scenario": "base",
        "financial": {
            "base": {
                "demand_uplift_pct": 0.0,
                "stockout_recovery_uplift_pct": 0.0,
                "pack_revenue_impact_pct": 0.0,
                "pack_consolidation_benefit_multiplier": 1.0,
                "cogs_ratio": 0.60,
                "overhead_ratio": 0.12,
                "carrying_cost_rate": 0.20,
            }
        },
    }

    master_df = pd.DataFrame(
        [{"SkuId": "SKU_1", "Price": 100, "UnitCost": 60, "SalesOrderQty": 10, "OnHandQty": 100}]
    )

    state = PipelineState(config=config, master_df=master_df, metadata={})

    # Inject fake pack size recommendations to avoid error
    pack_res = AgentResult("Pack Size Optimization", "success")
    pack_res.dataframes["recommendations_df"] = pd.DataFrame(
        [
            # If carrying cost is base, say PackQty matches average inventory (100 -> avg inventory 100, pack 200)
            # We just want to check units and revenue right now.
            {"SkuId": "SKU_1", "RecommendedPackQty": 200}
        ]
    )
    state.agent_results["Pack Size Optimization"] = pack_res

    result = AgentResult("Financial Impact", "pending")
    agent._run(state, result)

    fin_df = result.dataframes["financial_table_df"]
    assert len(fin_df) == 1
    row = fin_df.iloc[0]

    # Invariants for neutral scenario
    import pytest

    assert row["Scenario_Units"] == pytest.approx(row["Baseline_Units"])
    assert row["Scenario_Revenue"] == pytest.approx(row["Baseline_Revenue"])

    # Check that all effects are exactly 0
    assert row["Revenue_Effect"] == pytest.approx(0.0)
    assert row["COGS_Effect"] == pytest.approx(0.0)
    assert row["Carrying_Cost_Effect"] == pytest.approx(0.0)
    assert row["Pack_Conversion_Effect"] == pytest.approx(0.0)
    assert row["Overhead_Effect"] == pytest.approx(0.0)
    assert row["Total_Contribution_Change"] == pytest.approx(0.0)
    assert row["Scenario_Operating_Contribution"] == pytest.approx(
        row["Baseline_Operating_Contribution"]
    )

    # Mathematical identity checks
    assert row["Total_Contribution_Change"] == pytest.approx(
        row["Revenue_Effect"]
        + row["COGS_Effect"]
        + row["Carrying_Cost_Effect"]
        + row["Pack_Conversion_Effect"]
        + row["Overhead_Effect"]
    )
    assert row["Scenario_Operating_Contribution"] == pytest.approx(
        row["Baseline_Operating_Contribution"] + row["Total_Contribution_Change"]
    )


def test_financial_scenario_impact():
    agent = FinancialImpactAgent()
    config = {
        "active_scenario": "optimistic",
        "financial": {
            "optimistic": {
                "demand_uplift_pct": 0.10,  # 10% uplift
                "stockout_recovery_uplift_pct": 0.0,
                "pack_revenue_impact_pct": 0.05,  # 5% revenue increase
                "pack_consolidation_benefit_multiplier": 0.95,  # 5% reduction in COGS rate
                "cogs_ratio": 0.60,
                "overhead_ratio": 0.12,
                "carrying_cost_rate": 0.20,
            }
        },
    }

    master_df = pd.DataFrame(
        [{"SkuId": "SKU_1", "Price": 100, "UnitCost": 60, "SalesOrderQty": 10, "OnHandQty": 100}]
    )

    state = PipelineState(config=config, master_df=master_df, metadata={})
    pack_res = AgentResult("Pack Size Optimization", "success")
    pack_res.dataframes["recommendations_df"] = pd.DataFrame(
        [{"SkuId": "SKU_1", "RecommendedPackQty": 200}]
    )
    state.agent_results["Pack Size Optimization"] = pack_res

    result = AgentResult("Financial Impact", "pending")
    agent._run(state, result)

    row = result.dataframes["financial_table_df"].iloc[0]

    # 10% uplift in units
    assert round(row["Scenario_Units"], 2) == round(row["Baseline_Units"] * 1.10, 2)
    # Revenue is units * price * 1.05
    assert round(row["Scenario_Revenue"], 2) == round(
        row["Scenario_Units"] * row["Baseline_Unit_Price"] * 1.05, 2
    )
    # Scenario COGS is scenario_units * cost * 0.60 * 0.95
    assert round(row["Scenario_COGS"], 2) == round(row["Scenario_Units"] * 60 * 0.60 * 0.95, 2)
