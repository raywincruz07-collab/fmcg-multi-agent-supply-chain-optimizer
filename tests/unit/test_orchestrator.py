import pandas as pd
from fmcg_supply_chain.orchestration.state import PipelineState


def test_pipeline_state_trace():
    config = {"test": 1}
    df = pd.DataFrame()
    state = PipelineState(config=config, master_df=df, metadata={})

    state.log_trace("TestAgent", "Action", "Detail")

    assert len(state.trace) == 1
    assert state.trace[0]["agent"] == "TestAgent"
    assert state.trace[0]["action"] == "Action"
    assert state.trace[0]["details"] == "Detail"
