import pytest
import pandas as pd
from fmcg_supply_chain.agents.dispatch import DispatchOptimizationAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult


def test_graph_connectivity_and_routes():
    """Invalid routes must produce a controlled failure/exclusion."""
    agent = DispatchOptimizationAgent()

    # P_1 connects to Customer, P_2 is isolated
    edges = pd.DataFrame({"source": ["P_1"], "target": ["Customer"]})

    config = {"dispatch": {"cost_per_hop": 50}}
    state = PipelineState(config=config, master_df=pd.DataFrame(), metadata={"graph_edges": edges})

    result = AgentResult("Disp", "pending")
    agent._run(state, result)

    paths = result.dataframes["path_df"]
    # Only 1 valid path should be found
    assert len(paths) == 1
    assert paths.iloc[0]["SourcePlant"] == "P_1"
    assert paths.iloc[0]["Destination"] == "Customer"
    assert paths.iloc[0]["Hops"] == 1
    assert paths.iloc[0]["PathCost"] == 50
