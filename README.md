# FMCG Multi-Agent Supply Chain Optimizer

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
[![CI](https://github.com/raywincruz07-collab/fmcg-multi-agent-supply-chain-optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/raywincruz07-collab/fmcg-multi-agent-supply-chain-optimizer/actions/workflows/ci.yml)

**Developed and maintained by Raywin Cruz.**

This repository contains a deterministic decision-support orchestration pipeline for FMCG supply chains. It simulates data processing across five distinct stages: Demand Forecasting, Pack Size Optimization, Financial Impact Analysis, Production Planning, and Dispatch Network Routing.

## Dashboard Preview

![FMCG Multi-Agent Supply Chain Optimizer dashboard](assets/dashboard-overview.png)

## Features

- **Demand Intelligence:** Compares Random Forest against robust time-series baselines (Naive, Seasonal Naive, Rolling Mean) using a Chronological train-validation-test evaluation, where validation performance selects the model and the untouched test period reports final performance.
- **Pack-Size Recommendations:** Provides actionable packing guidelines constrained by Minimum Order Quantities (MOQs) and case-multiples.
- **Financial Scenario Modelling:** Generates Conservative, Base, and Optimistic revenue and operating-contribution scenario estimates.
- **Production & Dispatch:** Simulates capacity-constrained Economic Order Quantity (EOQ) targets and true NetworkX graph routing.
- **Transparent Execution Trace:** Orchestrator logs all deterministic decisions without artificial benchmark clamping or LLM "hallucinations."
  <br>
  ![Deterministic multi-agent execution trace](assets/agent-trace.png)
- **Demo Dashboard:** A clean Streamlit application reading purely from generated artifacts, eliminating execution latency in the presentation layer.

## Architecture & Blueprint

```mermaid
flowchart TD
    Data[(Data Layer)] --> A[Demand Intelligence Agent]
    A --> B[Pack Size Agent]
    B --> C[Financial Agent]
    B --> D[Production Agent]
    D --> E[Dispatch Agent]
    E --> Dash[Streamlit Dashboard]
```

This repository serves as an integration blueprint. In a potential SAP-integrated architecture:
- **Demand Intelligence:** Deployed via **SAP BTP AI Core** (Model Serving).
- **Pack Size Optimization:** Executed via **SAP HANA Cloud / Joule Agents** (Decision Layer).
- **Financial Impact:** Visualized within **SAP Analytics Cloud**.
- **Production & Dispatch:** Handled by **SAP IBP** and **SAP TM**.

> [!NOTE]
> **No live SAP connection exists.** This project acts as a standalone simulation and conceptual blueprint for what an SAP-integrated agentic supply-chain might look like.

## Quickstart

This application is built to run immediately for demonstration purposes.

```bash
# 1. Clone the repository
git clone https://github.com/raywincruz07-collab/fmcg-multi-agent-supply-chain-optimizer.git
cd fmcg-multi-agent-supply-chain-optimizer

# 2. Install dependencies
pip install -e .

# 3. Launch the Dashboard
streamlit run app/streamlit_app.py
```

> [!IMPORTANT]
> **Default dashboard mode uses committed generated demonstration artifacts** located in `demo_artifacts/`. To run the pipeline yourself, execute `python scripts/run_pipeline.py --config configs/default.yaml`. Runtime pipeline outputs go to the git-ignored `artifacts/` directory.

## Datasets

The default demonstration uses generated data following a **SupplyGraph-inspired schema**. Due to size limitations and licensing, the original SupplyGraph (Wasi et al., AAAI 2024) raw datasets are not included. The pipeline gracefully falls back to generating a coherent, valid sample dataset if the raw source is missing.

To run with the real dataset:
1. Review the data layout instructions in `scripts/download_data.py`.
2. Place the `Temporal Data` and `Nodes` directories into `data/raw/supplygraph/`.

## Project Structure

```text
├── .github/workflows/    # CI Pipeline
├── app/                  # Streamlit Dashboard (Presentation layer)
├── demo_artifacts/       # Lightweight committed artifacts used by the default dashboard
├── artifacts/            # Local pipeline outputs, ignored by Git
├── assets/               # Recruiter-facing dashboard screenshots
├── configs/              # Scenario definitions (default.yaml)
├── data/                 # Sample generated data and raw directories
├── docs/                 # Documentation and methodology
├── scripts/              # Pipeline execution and data generation
├── src/fmcg_supply_chain/
│   ├── agents/           # The 5 pipeline agents
│   ├── data/             # Dimensional data loaders
│   └── orchestration/    # Orchestrator and state tracking
└── tests/                # Pytest unit and integration tests
```

## Verified Capabilities & Transparency

- **Forecasting Evaluation:** Chronological evaluation and per-SKU model selection using validation WAPE. In the included generated-data demonstration, baseline models outperform Random Forest for most evaluated SKUs. This result describes the demo dataset and is not a general forecasting benchmark.
- **Financial Scenarios:** Financial results are scenario estimates configured via `configs/default.yaml`, not observed historical outcomes. 
- **Routing:** Dispatch results are graph-based scenario outputs calculated via shortest-path algorithms over a constrained graph.

## Limitations

- **No Live Integration:** No live SAP connection exists; it is a conceptual blueprint.
- **Generated Data:** By default, runs on generated sample data.
- **Not in Production:** This is a deterministic simulation, not deployed to production.
- **Financial Estimates:** Financial results are scenario estimates, not observed outcomes.

## Testing

The pipeline is verified by a 23-test suite covering all agents and integration points:

```bash
python -m pytest -v
```


## License

This project is licensed under the [MIT License](LICENSE).
