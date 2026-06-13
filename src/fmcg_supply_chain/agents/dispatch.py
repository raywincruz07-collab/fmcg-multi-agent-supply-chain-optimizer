import pandas as pd
import networkx as nx
from fmcg_supply_chain.agents.base import BaseAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult


class DispatchOptimizationAgent(BaseAgent):
    def __init__(self):
        super().__init__("Dispatch Optimization")

    def _run(self, state: PipelineState, result: AgentResult) -> None:
        dispatch_cfg = state.config.get("dispatch", {})
        cost_per_hop = dispatch_cfg.get("cost_per_hop", 50)

        edges_df = state.metadata.get("graph_edges", pd.DataFrame())

        if edges_df.empty:
            result.status = "error"
            result.warnings.append("No graph edges available to build network.")
            return

        # Build NetworkX directed graph
        G = nx.DiGraph()

        for _, row in edges_df.iterrows():
            source = row.get("source")
            target = row.get("target")
            if source and target:
                # In a real scenario, edge weights would come from distance or carrier cost.
                # Here we use a uniform unit weight to count hops if no explicit cost is provided.
                weight = row.get("weight", cost_per_hop)
                G.add_edge(source, target, weight=weight)

        # Find path from all Plants to Customers
        # For simplicity, we find shortest paths from any node starting with 'P_' (Plant) to 'Customer'
        plants = [n for n in G.nodes if str(n).startswith("P_")]
        customers = [n for n in G.nodes if str(n) == "Customer"]

        if not customers:
            result.warnings.append(
                "No 'Customer' sink node found in graph. Using any leaf nodes as destinations."
            )
            out_degrees = G.out_degree()
            customers = [n for n, d in out_degrees if d == 0]

        paths_info = []

        for p in plants:
            for c in customers:
                try:
                    # Calculate shortest path by weight
                    path = nx.shortest_path(G, source=p, target=c, weight="weight")
                    path_cost = nx.shortest_path_length(G, source=p, target=c, weight="weight")
                    hops = len(path) - 1

                    paths_info.append(
                        {
                            "SourcePlant": p,
                            "Destination": c,
                            "Path": " -> ".join(map(str, path)),
                            "Hops": hops,
                            "PathCost": path_cost,
                        }
                    )
                except nx.NetworkXNoPath:
                    continue

        paths_df = pd.DataFrame(paths_info)
        result.dataframes["path_df"] = paths_df

        # Calculate summary metrics (genuine, not artificially clamped)
        avg_hops = paths_df["Hops"].mean() if len(paths_df) > 0 else 0
        avg_cost = paths_df["PathCost"].mean() if len(paths_df) > 0 else 0

        result.metrics["total_plants"] = len(plants)
        result.metrics["average_network_hops"] = round(avg_hops, 2)
        result.metrics["average_path_cost"] = round(avg_cost, 2)

        result.rationale.append(
            f"Derived {len(paths_info)} routing paths. Calculated true network hops and costs using NetworkX without enforcing benchmark bounds."
        )
        state.log_trace(
            self.name,
            "Routing Optimization",
            f"Found {len(paths_info)} feasible plant-to-customer paths.",
        )
