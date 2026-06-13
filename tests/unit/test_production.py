import pandas as pd
from fmcg_supply_chain.agents.production import ProductionPlanningAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult


def _setup_agent_and_state(capacity=10000):
    agent = ProductionPlanningAgent()
    demand_df = pd.DataFrame({"SkuId": ["SKU_1"], "ForecastQty": [10]})
    config = {
        "production": {
            "holding_cost_per_unit": 0.5,
            "setup_cost_per_batch": 500,
            "max_plant_capacity_per_day": capacity,
        }
    }
    state = PipelineState(config=config, master_df=pd.DataFrame(), metadata={})
    demand_res = AgentResult("Demand Intelligence", "success")
    demand_res.dataframes["forecast_df"] = demand_df
    state.agent_results["Demand Intelligence"] = demand_res

    pack_res = AgentResult("Pack Size Optimization", "success")
    pack_res.dataframes["recommendations_df"] = pd.DataFrame(
        {"SkuId": ["SKU_1"], "RecommendedPackQty": [10]}
    )
    state.agent_results["Pack Size Optimization"] = pack_res
    return agent, state


def test_production_eoq_calculation():
    """Batch or EOQ calculation."""
    agent, state = _setup_agent_and_state()
    result = AgentResult("Prod", "pending")
    agent._run(state, result)
    sched = result.dataframes["production_schedule_df"]
    sku_eoq = sched.iloc[0]["OptimalBatchSize_EOQ"]
    # daily demand = 10 -> annual = 3650
    # eoq = sqrt((2 * 3650 * 500) / 0.5) = sqrt(7300000) ~= 2701.85
    assert 2700 <= sku_eoq <= 2703


def test_production_capacity_feasibility():
    """Capacity feasibility."""
    agent, state = _setup_agent_and_state()
    result = AgentResult("Prod", "pending")
    agent._run(state, result)
    sched = result.dataframes["production_schedule_df"]
    assert sched.iloc[0]["CapacityFeasible"]


def test_production_capacity_bound_behaviour():
    """Capacity-bound behaviour."""
    # Extremely low capacity
    agent, state = _setup_agent_and_state(capacity=1000)
    result = AgentResult("Prod", "pending")
    agent._run(state, result)
    sched = result.dataframes["production_schedule_df"]
    # Bound by capacity
    assert sched.iloc[0]["OptimalBatchSize_EOQ"] == 1000
    assert not sched.iloc[0]["CapacityFeasible"]


def test_production_schedule_schema():
    """Production schedule schema."""
    agent, state = _setup_agent_and_state()
    result = AgentResult("Prod", "pending")
    agent._run(state, result)
    sched = result.dataframes["production_schedule_df"]
    required_cols = ["SkuId", "AnnualDemand", "OptimalBatchSize_EOQ", "CapacityFeasible"]
    for col in required_cols:
        assert col in sched.columns


def test_production_deterministic_fixed_input():
    """Deterministic fixed-input output."""
    agent1, state1 = _setup_agent_and_state()
    res1 = AgentResult("Prod1", "pending")
    agent1._run(state1, res1)

    agent2, state2 = _setup_agent_and_state()
    res2 = AgentResult("Prod2", "pending")
    agent2._run(state2, res2)

    pd.testing.assert_frame_equal(
        res1.dataframes["production_schedule_df"], res2.dataframes["production_schedule_df"]
    )
