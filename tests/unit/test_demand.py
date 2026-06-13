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
    """Train maximum date must be earlier than val min, and val max earlier than test min."""
    agent = DemandIntelligenceAgent()

    # Need at least validation(10) + test(10) + train(30) = 50 days
    dates = pd.date_range("2023-01-01", periods=60)
    df = pd.DataFrame(
        {
            "Date": dates,
            "SkuId": ["SKU_1"] * 60,
            "SalesOrderQty": np.random.randint(10, 50, size=60),
        }
    )

    config = {"demand": {"validation_days": 10, "test_days": 10, "minimum_training_days": 30}}
    state = PipelineState(config=config, master_df=df, metadata={})
    result = AgentResult(agent_name="Demand", status="pending")

    agent._run(state, result)

    metrics = result.dataframes["metrics_df"].iloc[0]

    assert metrics["Train_End"] < metrics["Val_Start"]
    assert metrics["Val_End"] < metrics["Test_Start"]


def test_model_selection_independence():
    """Test labels are not used for model selection, and altering test labels does not change the model."""
    agent = DemandIntelligenceAgent()
    dates = pd.date_range("2023-01-01", periods=60)

    # Base data: constant train/val
    base_sales = [50] * 50 + [100] * 10
    df1 = pd.DataFrame({"Date": dates, "SkuId": ["SKU_1"] * 60, "SalesOrderQty": base_sales})

    config = {"demand": {"validation_days": 10, "test_days": 10, "minimum_training_days": 30}}

    state1 = PipelineState(config=config, master_df=df1, metadata={})
    res1 = AgentResult(agent_name="Demand", status="pending")
    agent._run(state1, res1)
    model1 = res1.dataframes["metrics_df"].iloc[0]["SelectedModel"]

    # Alter the test labels drastically
    alt_sales = [50] * 50 + [999] * 10
    df2 = pd.DataFrame({"Date": dates, "SkuId": ["SKU_1"] * 60, "SalesOrderQty": alt_sales})

    state2 = PipelineState(config=config, master_df=df2, metadata={})
    res2 = AgentResult(agent_name="Demand", status="pending")
    agent._run(state2, res2)
    model2 = res2.dataframes["metrics_df"].iloc[0]["SelectedModel"]

    # Model should be identical since selection is independent of test set
    assert model1 == model2


def test_insufficient_history_handled():
    """SKUs with less than minimum required history are explicitly skipped."""
    agent = DemandIntelligenceAgent()
    dates = pd.date_range("2023-01-01", periods=40)
    df = pd.DataFrame({"Date": dates, "SkuId": ["SKU_1"] * 40, "SalesOrderQty": [10] * 40})

    config = {
        "demand": {"validation_days": 10, "test_days": 10, "minimum_training_days": 30}
    }  # Needs 50
    state = PipelineState(config=config, master_df=df, metadata={})
    result = AgentResult(agent_name="Demand", status="pending")

    agent._run(state, result)

    # Should skip the SKU and flag as excluded
    assert result.metrics["Excluded_SKUs"] == 1
    assert "Skipping SKU_1: insufficient data history" in result.rationale[0]
