import numpy as np
import pandas as pd
from fmcg_supply_chain.agents.demand import DemandIntelligenceAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult


def test_wape_calculation():
    agent = DemandIntelligenceAgent()
    y_true = np.array([10, 20, 30])
    y_pred = np.array([10, 20, 30])
    assert agent._wape(y_true, y_pred) == 0.0

    y_true_2 = np.array([10, 20, 30])
    y_pred_2 = np.array([12, 18, 30])
    wape = agent._wape(y_true_2, y_pred_2)
    assert abs(wape - 6.66) < 0.1


def test_wape_zero_division():
    agent = DemandIntelligenceAgent()
    y_true = np.array([0, 0, 0])
    y_pred = np.array([0, 0, 0])
    assert agent._wape(y_true, y_pred) == 0.0


def test_chronological_split_and_no_leakage():
    """Train maximum date must be earlier than test minimum date."""
    agent = DemandIntelligenceAgent()

    # 40 days of data
    dates = pd.date_range("2023-01-01", periods=40)
    df = pd.DataFrame(
        {
            "Date": dates,
            "SkuId": ["SKU_1"] * 40,
            "SalesOrderQty": np.random.randint(10, 50, size=40),
        }
    )

    config = {"demand": {"horizon_days": 10}}
    state = PipelineState(config=config, master_df=df, metadata={})
    result = AgentResult(agent_name="Demand", status="pending")

    agent._run(state, result)

    forecast_df = result.dataframes["forecast_df"]

    # Verify the test/forecast dates are strictly the last 10 days
    expected_test_dates = dates[-10:]
    assert (forecast_df["Date"].values == expected_test_dates).all()

    # Since we use 30 train days, train max is dates[29], test min is dates[30]
    assert dates[29] < forecast_df["Date"].min()


def test_model_selection_against_baselines():
    """Model selection correctly picks the lowest WAPE."""
    agent = DemandIntelligenceAgent()

    # Create data where a naive constant forecast is perfect
    dates = pd.date_range("2023-01-01", periods=40)
    df = pd.DataFrame(
        {"Date": dates, "SkuId": ["SKU_1"] * 40, "SalesOrderQty": [50] * 40}  # Constant demand
    )

    config = {"demand": {"horizon_days": 10}}
    state = PipelineState(config=config, master_df=df, metadata={})
    result = AgentResult(agent_name="Demand", status="pending")

    agent._run(state, result)
    metrics = result.dataframes["metrics_df"]

    # Naive Last should be absolutely perfect (0 WAPE) and be selected
    assert metrics.iloc[0]["BestModel"] in ["naive_last", "rolling_mean_7d", "seasonal_naive_7d"]
    assert metrics.iloc[0]["WAPE"] == 0.0
