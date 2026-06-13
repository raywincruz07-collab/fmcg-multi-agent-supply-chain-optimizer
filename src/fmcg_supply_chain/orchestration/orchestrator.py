import logging
from pathlib import Path
from typing import Dict, Any

from fmcg_supply_chain.orchestration.state import PipelineState
from fmcg_supply_chain.data.loaders import UnifiedDataLoader, validate_schema
from fmcg_supply_chain.agents import (
    DemandIntelligenceAgent,
    PackSizeOptimizationAgent,
    FinancialImpactAgent,
    ProductionPlanningAgent,
    DispatchOptimizationAgent,
)


class AgentOrchestrator:
    """
    Deterministic decision-support orchestrator for the FMCG supply chain.
    Runs agents sequentially and logs decisions to a pipeline trace.
    """

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.logger = logging.getLogger(__name__)

    def run_pipeline(self, config: Dict[str, Any]) -> PipelineState:
        self.logger.info("Starting orchestrated pipeline.")

        # 1. Load Data
        loader = UnifiedDataLoader(self.root_dir)
        fact_df, metadata = loader.load()
        validate_schema(fact_df, metadata.get("sku_mappings"))

        # 2. Initialize State
        state = PipelineState(config=config, master_df=fact_df, metadata=metadata)
        state.log_trace("Orchestrator", "Data Loaded", f"Loaded {len(fact_df)} facts.")

        # 3. Instantiate Agents
        agents = [
            DemandIntelligenceAgent(),
            PackSizeOptimizationAgent(),
            FinancialImpactAgent(),
            ProductionPlanningAgent(),
            DispatchOptimizationAgent(),
        ]

        # 4. Execute Pipeline
        for agent in agents:
            self.logger.info(f"Running agent: {agent.name}")
            result = agent.execute(state)
            if result.status == "error":
                self.logger.error(f"Agent {agent.name} failed. Halting pipeline.")
                self.logger.error(f"Warnings: {result.warnings}")
                break

        state.log_trace("Orchestrator", "Pipeline Complete", "Finished sequential execution.")
        self.logger.info("Pipeline execution complete.")
        return state
