import pandas as pd
import networkx as nx
from fmcg_supply_chain.agents.base import BaseAgent
from fmcg_supply_chain.orchestration.state import PipelineState, AgentResult
from itertools import islice


class DispatchOptimizationAgent(BaseAgent):
    def __init__(self):
        super().__init__("Dispatch Optimization")

    def _run(self, state: PipelineState, result: AgentResult) -> None:
        dispatch_cfg = state.config.get("dispatch", {})
        cost_per_hop = dispatch_cfg.get("cost_per_hop", 50)
        max_candidate_routes = dispatch_cfg.get("max_candidate_routes", 5)
        max_route_hops = dispatch_cfg.get("max_route_hops", 6)

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
                weight = row.get("cost", cost_per_hop)
                capacity = row.get("capacity", float("inf"))
                G.add_edge(source, target, weight=weight, capacity=capacity)

        plants = [n for n in G.nodes if str(n).startswith("P_")]
        customers = [n for n in G.nodes if str(n).startswith("Customer")]

        if not customers:
            result.warnings.append(
                "No 'Customer' sink node found in graph. Using any leaf nodes as destinations."
            )
            out_degrees = G.out_degree()
            customers = [n for n, d in out_degrees if d == 0]

        paths_info = []

        total_routes_evaluated = 0

        for p in plants:
            for c in customers:
                if not nx.has_path(G, source=p, target=c):
                    continue

                try:
                    candidates = list(
                        islice(
                            nx.shortest_simple_paths(G, source=p, target=c, weight="weight"),
                            max_candidate_routes,
                        )
                    )

                    if not candidates:
                        continue

                    # Evaluate candidates for capacity feasibility
                    best_path = None
                    best_cost = float("inf")
                    best_hops = 0
                    best_feasibility = False
                    best_reason = ""

                    for candidate in candidates:
                        hops = len(candidate) - 1
                        if hops > max_route_hops:
                            continue

                        total_routes_evaluated += 1

                        path_cost = sum(
                            G[candidate[i]][candidate[i + 1]]["weight"]
                            for i in range(len(candidate) - 1)
                        )
                        path_capacity = min(
                            G[candidate[i]][candidate[i + 1]]["capacity"]
                            for i in range(len(candidate) - 1)
                        )

                        # In real world, demand dictates capacity feasibility. For demo, we assume capacity > 50 is feasible.
                        is_feasible = path_capacity > 50

                        if is_feasible and path_cost < best_cost:
                            best_path = candidate
                            best_cost = path_cost
                            best_hops = hops
                            best_feasibility = True
                            best_reason = "Lowest cost feasible route"

                    if best_path is None:
                        # Fallback to the shortest infeasible if no feasible routes
                        best_path = candidates[0]
                        best_cost = sum(
                            G[best_path[i]][best_path[i + 1]]["weight"]
                            for i in range(len(best_path) - 1)
                        )
                        best_hops = len(best_path) - 1
                        best_feasibility = False
                        best_reason = "Shortest route (infeasible capacity)"

                    paths_info.append(
                        {
                            "Source": p,
                            "Destination": c,
                            "Candidate_Route_Count": len(candidates),
                            "Selected_Route": " -> ".join(map(str, best_path)),
                            "Path_Cost": best_cost,
                            "Number_of_Hops": best_hops,
                            "Capacity_Feasibility": best_feasibility,
                            "Selection_Reason": best_reason,
                        }
                    )

                    state.log_trace(
                        self.name,
                        f"Route Selection ({p} -> {c})",
                        f"Selected {' -> '.join(map(str, best_path))} out of {len(candidates)} candidates. "
                        f"Cost: {best_cost}. Capacity > 50 requirement met: {best_feasibility}. "
                        f"Reason: {best_reason}.",
                    )
                except nx.NetworkXNoPath:
                    continue

        paths_df = pd.DataFrame(paths_info)
        result.dataframes["path_df"] = paths_df

        if len(paths_df) > 0:
            avg_hops = paths_df["Number_of_Hops"].mean()
            avg_cost = paths_df["Path_Cost"].mean()
            result.metrics["total_plants"] = len(plants)
            result.metrics["average_network_hops"] = round(avg_hops, 2)
            result.metrics["average_path_cost"] = round(avg_cost, 2)
            result.metrics["total_candidate_routes_evaluated"] = total_routes_evaluated

            result.rationale.append(
                f"Evaluated {total_routes_evaluated} route candidates up to max_hops={max_route_hops}. Extracted relative path-cost improvement across available choices."
            )
        else:
            result.rationale.append("No viable paths found from plants to customers.")

        state.log_trace(
            self.name,
            "Routing Optimization",
            f"Found {len(paths_info)} plant-to-customer best paths from candidates.",
        )
