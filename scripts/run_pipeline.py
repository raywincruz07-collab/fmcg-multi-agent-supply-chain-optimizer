import argparse
import yaml
from pathlib import Path
import pandas as pd
import json
from datetime import datetime
import os

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fmcg_supply_chain.orchestration.orchestrator import AgentOrchestrator


def main():
    parser = argparse.ArgumentParser(description="FMCG Supply Chain Pipeline")
    parser.add_argument(
        "--config", type=str, default="configs/default.yaml", help="Path to configuration file"
    )
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent
    config_path = root_dir / args.config

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    print("================================================================")
    print("           FMCG Multi-Agent Supply Chain Optimizer              ")
    print("================================================================")

    orchestrator = AgentOrchestrator(root_dir)
    state = orchestrator.run_pipeline(config)

    # Save artifacts
    env_artifact_dir = os.environ.get("ARTIFACT_DIR")
    if env_artifact_dir:
        artifacts_path = Path(env_artifact_dir)
        if artifacts_path.is_absolute():
            artifacts_dir = artifacts_path
        else:
            artifacts_dir = root_dir / artifacts_path
    else:
        artifacts_dir = root_dir / "artifacts"

    artifacts_dir.mkdir(parents=True, exist_ok=True)

    print("\n--- Saving Artifacts ---")
    for agent_name, result in state.agent_results.items():
        if result.status == "error":
            print(f"[!] Agent {agent_name} failed. Check traces.")
            continue

        safe_name = agent_name.lower().replace(" ", "_")
        for df_name, df in result.dataframes.items():
            out_path = artifacts_dir / f"{safe_name}_{df_name}.csv"
            df.to_csv(out_path, index=False)
            print(f"Saved: {out_path.name} ({len(df)} rows)")

    # Save Trace
    trace_df = pd.DataFrame(state.trace)
    trace_path = artifacts_dir / "orchestration_trace.csv"
    trace_df.to_csv(trace_path, index=False)
    print(f"Saved: {trace_path.name}")

    # Save Metrics summary
    metrics = []
    for agent_name, result in state.agent_results.items():
        for k, v in result.metrics.items():
            metrics.append({"Agent": agent_name, "Metric": k, "Value": v})

    if metrics:
        metrics_df = pd.DataFrame(metrics)
        metrics_path = artifacts_dir / "pipeline_metrics.csv"
        metrics_df.to_csv(metrics_path, index=False)
        print(f"Saved: {metrics_path.name}")

    # Generate metadata schema
    schema_metadata = {
        "schema_version": "1.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "config_name": args.config,
        "data_mode": "generated_demo",
        "pipeline_version": "1.0.0",
        "artifacts_generated": [f.name for f in artifacts_dir.glob("*.csv")],
        "configuration_used": config,
    }
    with open(artifacts_dir / "metadata.json", "w") as f:
        json.dump(schema_metadata, f, indent=4)
    print("Saved: metadata.json")

    print("\nPipeline execution complete. You can now launch the dashboard:")
    print("    streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
