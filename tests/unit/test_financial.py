import pytest
import pandas as pd
from fmcg_supply_chain.agents.financial import FinancialImpactAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult


def test_financial_calculations_no_clamping():
    """Financial outputs must change predictably when scenario assumptions change."""
    agent = FinancialImpactAgent()

    master_df = pd.DataFrame(
        {
            "SkuId": ["SKU_1"],
            "Price": [100.0],
            "UnitCost": [50.0],
            "SalesOrderQty": [10],
            "OnHandQty": [50],
        }
    )

    reco_df = pd.DataFrame({"SkuId": ["SKU_1"], "RecommendedPackQty": [200]})

    config = {
        "active_scenario": "conservative",
        "financial": {
            "conservative": {
                "cogs_ratio": 0.6,
                "overhead_ratio": 0.1,
                "carrying_cost_rate": 0.1,
                "demand_uplift_pct": 0.0,
                "pack_consolidation_benefit_multiplier": 1.0,
            },
            "optimistic": {
                "cogs_ratio": 0.6,
                "overhead_ratio": 0.1,
                "carrying_cost_rate": 0.1,
                "demand_uplift_pct": 0.1,
                "pack_consolidation_benefit_multiplier": 0.9,
            },
        },
    }

    state = PipelineState(config=config, master_df=master_df, metadata={})

    pack_res = AgentResult("Pack Size", "success")
    pack_res.dataframes["recommendations_df"] = reco_df
    state.agent_results["Pack Size Optimization"] = pack_res

    result_cons = AgentResult("Fin", "pending")
    agent._run(state, result_cons)

    cons_df = result_cons.dataframes["financial_table_df"]
    cons_pbt = cons_df.iloc[0]["After_PBT"]

    # Now optimistic
    state.config["active_scenario"] = "optimistic"
    result_opt = AgentResult("Fin", "pending")
    agent._run(state, result_opt)

    opt_df = result_opt.dataframes["financial_table_df"]
    opt_pbt = opt_df.iloc[0]["After_PBT"]

    # Optimistic should yield higher PBT (due to demand uplift and cost reduction)
    assert opt_pbt > cons_pbt

    # Check that np.clip or benchmarks are NOT in the file via text inspection in the audit later
