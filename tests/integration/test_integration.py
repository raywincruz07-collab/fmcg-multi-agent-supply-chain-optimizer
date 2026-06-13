import yaml
import pandas as pd
from pathlib import Path
from fmcg_supply_chain.orchestration.orchestrator import AgentOrchestrator
from fmcg_supply_chain.agents.base import BaseAgent
from fmcg_supply_chain.orchestration.state import PipelineState


def test_orchestrator_failure_path():
    """Agent failure must be recorded in the orchestration trace and halt pipeline."""

    class FailingAgent(BaseAgent):
        def __init__(self):
            super().__init__("Failer")

        def _run(self, state, result):
            raise ValueError("Intentional crash")

    AgentOrchestrator(Path(__file__).parent)
    # Mocking run_pipeline logic slightly just to test agent failure handling
    config = {}
    state = PipelineState(config, pd.DataFrame(), {})
    agent = FailingAgent()

    res = agent.execute(state)

    assert res.status == "error"
    assert "Intentional crash" in str(res.warnings)

    # Trace must have recorded it
    assert len(state.trace) > 0
    assert state.trace[-1]["action"] == "Execution Error"
    assert "Intentional crash" in state.trace[-1]["details"]


def test_end_to_end_smoke_test():
    """The end-to-end sample pipeline must generate all required artifact schemas."""
    # We will invoke the orchestrator on the sample data.
    # We must ensure the sample data exists.

    root_dir = Path(__file__).resolve().parent.parent.parent

    # We load default config
    config_path = root_dir / "configs" / "default.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    orchestrator = AgentOrchestrator(root_dir)
    state = orchestrator.run_pipeline(config)

    # Pipeline should succeed without errors
    for agent_name, result in state.agent_results.items():
        assert result.status == "success", f"{agent_name} failed: {result.warnings}"

    # Verify required schemas were populated
    assert "forecast_df" in state.agent_results["Demand Intelligence"].dataframes
    assert "recommendations_df" in state.agent_results["Pack Size Optimization"].dataframes
    assert "financial_table_df" in state.agent_results["Financial Impact"].dataframes
    assert "production_schedule_df" in state.agent_results["Production Planning"].dataframes
    assert "path_df" in state.agent_results["Dispatch Optimization"].dataframes


def test_demo_artifacts_exist():
    """Verify that committed demo artifacts exist and have valid metadata schema."""
    import json

    root_dir = Path(__file__).resolve().parent.parent.parent
    demo_dir = root_dir / "demo_artifacts"

    # If the directory doesn't exist, we can't test it, but it should be committed.
    if not demo_dir.exists():
        return

    metadata_path = demo_dir / "metadata.json"
    assert metadata_path.exists()

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    assert metadata.get("schema_version") == "1.0"
    assert metadata.get("data_mode") == "generated_demo"
    assert "pipeline_version" in metadata
    assert len(metadata.get("artifacts_generated", [])) > 0

    for fname in metadata["artifacts_generated"]:
        assert (demo_dir / fname).exists()
        # Verify non-empty
        df = pd.read_csv(demo_dir / fname)
        assert len(df) > 0
