import pandas as pd
from fmcg_supply_chain.agents.dispatch import DispatchOptimizationAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult


def test_dispatch_alternative_routes_and_capacity():
    agent = DispatchOptimizationAgent()

    # P_1 connects to S_1 and S_2. Both connect to Customer_A.
    # Route 1: P_1 -> S_1 -> Customer_A (Cost 10 + 10 = 20, Capacity 10) (Infeasible, capacity < 50)
    # Route 2: P_1 -> S_2 -> Customer_A (Cost 50 + 50 = 100, Capacity 100) (Feasible, should be selected)

    edges = pd.DataFrame(
        [
            {"source": "P_1", "target": "S_1", "cost": 10, "capacity": 10},
            {"source": "S_1", "target": "Customer_A", "cost": 10, "capacity": 100},
            {"source": "P_1", "target": "S_2", "cost": 50, "capacity": 100},
            {"source": "S_2", "target": "Customer_A", "cost": 50, "capacity": 100},
        ]
    )

    config = {"dispatch": {"max_candidate_routes": 5, "max_route_hops": 6}}
    state = PipelineState(config=config, metadata={"graph_edges": edges}, master_df=pd.DataFrame())
    result = AgentResult(agent_name="Dispatch", status="pending")

    agent._run(state, result)

    path_df = result.dataframes["path_df"]

    assert len(path_df) == 1
    row = path_df.iloc[0]

    assert row["Candidate_Route_Count"] == 2
    assert row["Capacity_Feasibility"]
    # The selected route must be the feasible one, even though it's more expensive
    assert "S_2" in row["Selected_Route"]
    assert row["Path_Cost"] == 100


def test_dispatch_disconnected_path():
    agent = DispatchOptimizationAgent()

    # P_2 has no path to any customer
    edges = pd.DataFrame(
        [
            {"source": "P_1", "target": "Customer_A", "cost": 10, "capacity": 100},
            {"source": "P_2", "target": "S_3", "cost": 10, "capacity": 100},
        ]
    )

    config = {"dispatch": {"max_candidate_routes": 5, "max_route_hops": 6}}
    state = PipelineState(config=config, metadata={"graph_edges": edges}, master_df=pd.DataFrame())
    result = AgentResult(agent_name="Dispatch", status="pending")

    agent._run(state, result)

    path_df = result.dataframes["path_df"]
    # Should only return a path for P_1, P_2 is quietly ignored or skipped
    assert len(path_df) == 1
    assert path_df.iloc[0]["Source"] == "P_1"


def test_dispatch_invalid_nodes():
    agent = DispatchOptimizationAgent()

    # Malformed edge missing target
    edges = pd.DataFrame(
        [
            {"source": "P_1", "target": None, "cost": 10, "capacity": 100},
        ]
    )

    config = {"dispatch": {"max_candidate_routes": 5, "max_route_hops": 6}}
    state = PipelineState(config=config, metadata={"graph_edges": edges}, master_df=pd.DataFrame())
    result = AgentResult(agent_name="Dispatch", status="pending")

    agent._run(state, result)

    # No valid customers found
    assert "No 'Customer' sink node found" in result.warnings[0]
