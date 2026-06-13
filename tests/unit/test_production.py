import pytest
import pandas as pd
from fmcg_supply_chain.agents.production import ProductionPlanningAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult


def test_production_capacity_and_eoq():
    """Production EOQ must calculate correctly."""
    agent = ProductionPlanningAgent()

    demand_df = pd.DataFrame({"SkuId": ["SKU_1"], "ForecastQty": [10]})

    config = {
        "production": {
            "holding_cost_per_unit": 0.5,
            "setup_cost_per_batch": 500,
            "max_plant_capacity_per_day": 10000,
        }
    }

    state = PipelineState(config=config, master_df=pd.DataFrame(), metadata={})
    demand_res = AgentResult("Demand Intelligence", "success")
    demand_res.dataframes["forecast_df"] = demand_df
    state.agent_results["Demand Intelligence"] = demand_res
    
    pack_res = AgentResult("Pack Size Optimization", "success")
    pack_res.dataframes["recommendations_df"] = pd.DataFrame({"SkuId": ["SKU_1"], "RecommendedPackQty": [10]})
    state.agent_results["Pack Size Optimization"] = pack_res
    
    result = AgentResult("Prod", "pending")
    agent._run(state, result)

    sched = result.dataframes["production_schedule_df"]
    sku_eoq = sched.iloc[0]["OptimalBatchSize_EOQ"]

    # daily demand = 10 -> annual = 3650
    # eoq = sqrt((2 * 3650 * 500) / 0.5) = sqrt(7300000) ~= 2701.85
    assert 2700 <= sku_eoq <= 2703
