# FMCG Multi-Agent Supply Chain Optimizer

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![CI](https://github.com/USERNAME/fmcg-multi-agent-supply-chain-optimizer/actions/workflows/ci.yml/badge.svg)

**Repository maintained and professionally refactored by Raywin Cruz. Original implementation contributions by Namrath Basavaraju.**

This repository contains a deterministic decision-support orchestration pipeline for FMCG supply chains. It simulates data processing across five distinct stages: Demand Forecasting, Pack Size Optimization, Financial Impact Analysis, Production Planning, and Dispatch Network Routing.

## Features

- **Demand Intelligence:** Compares Random Forest against robust time-series baselines (Naive, Seasonal Naive, Rolling Mean) using a strict chronological train/test split to prevent leakage.
- **Pack-Size Recommendations:** Provides actionable packing guidelines constrained by Minimum Order Quantities (MOQs) and case-multiples.
- **Financial Scenario Modelling:** Generates Conservative, Base, and Optimistic PBT/Revenue projections.
- **Production & Dispatch:** Simulates capacity-constrained Economic Order Quantity (EOQ) targets and true NetworkX graph routing.
- **Transparent Execution Trace:** Orchestrator logs all deterministic decisions without artificial benchmark clamping or LLM "hallucinations."
- **Demo Dashboard:** A clean Streamlit application reading purely from generated artifacts, eliminating execution latency in the presentation layer.

## Architecture & Blueprint

This repository serves as an integration blueprint. In a production environment:
- **Demand Intelligence:** Deployed via **SAP BTP AI Core** (Model Serving).
- **Pack Size Optimization:** Executed via **SAP HANA Cloud / Joule Agents** (Decision Layer).
- **Financial Impact:** Visualized within **SAP Analytics Cloud**.
- **Production & Dispatch:** Handled by **SAP IBP** and **SAP TM**.

## Quickstart

This application is built to run immediately using a deterministic sample dataset for demonstration purposes.

```bash
# 1. Clone the repository
git clone https://github.com/USERNAME/fmcg-multi-agent-supply-chain-optimizer.git
cd fmcg-multi-agent-supply-chain-optimizer

# 2. Install dependencies
pip install -e .

# 3. Generate sample data
python scripts/generate_sample_data.py

# 4. Run the orchestration pipeline
python scripts/run_pipeline.py --config configs/default.yaml

# 5. Launch the Dashboard
streamlit run app/streamlit_app.py
```

## Datasets

The raw data processing was developed around the **SupplyGraph** dataset structure (Wasi et al., AAAI 2024). Due to size limitations and licensing, the raw datasets are not included. The pipeline gracefully falls back to generating a coherent, valid sample dataset if the raw source is missing.

To run with the real dataset:
1. Review the data layout instructions in `scripts/download_data.py`.
2. Place the `Temporal Data` and `Nodes` directories into `data/raw/supplygraph/`.

*(Note: The M5 Kaggle Dataset, originally mixed into the codebase, has been isolated to `experiments/m5_forecasting_benchmark.py` to preserve architectural purity).*

## Project Structure

```text
├── .github/workflows/    # CI Pipeline
├── app/                  # Streamlit Dashboard (Presentation layer)
├── artifacts/            # Output from pipeline runs (ignored in Git)
├── configs/              # Scenario definitions (default.yaml)
├── data/                 # Sample generated data and raw directories
├── docs/                 # Migration inventory and notes
├── experiments/          # Standalone benchmarks (e.g. M5)
├── scripts/              # Pipeline execution and data generation
├── src/fmcg_supply_chain/
│   ├── agents/           # The 5 pipeline agents
│   ├── data/             # Dimensional data loaders
│   └── orchestration/    # Orchestrator and state tracking
└── tests/                # Pytest unit tests
```
