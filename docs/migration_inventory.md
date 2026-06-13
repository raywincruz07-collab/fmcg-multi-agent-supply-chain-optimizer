# Migration Inventory

This document tracks the initial state of the `fmcg-agentic-ai` repository and the decisions made during the refactoring process to `fmcg-multi-agent-supply-chain-optimizer`.

## Existing Authorship & Attribution
- **Original Implementation Author:** Namrath Basavaraju (MSc Data Science, University of Mannheim)
- **Datasets:**
  - SupplyGraph: Wasi et al., AAAI 2024
- **Refactoring Contributor & Maintainer:** Raywin Cruz

*Note: The new repository will clearly state: "Repository maintained and professionally refactored by Raywin Cruz. Original implementation contributions by Namrath Basavaraju."*

## Existing Features & Dashboard Pages
- **Streamlit App (`app.py`):**
  - Configurable UI with SKU, Plant, and Horizon filters.
  - 5 main tabs matching the 5 agents.
  - "Run All Agents" button that triggers pipeline execution directly in the UI.
  - Download buttons for artifacts.
  - SAP BTP AI Core Simulation toggle (purely decorative).
- **Existing Commands:**
  - `python orchestrator/orchestrator.py`
  - `streamlit run app.py`

## Existing Agents
1. **Demand Intelligence Agent:** Uses Random Forest to predict demand.
2. **Pack Size Optimization Agent:** Uses KMeans to cluster SKUs into fast, medium, and slow movers, providing pack configurations.
3. **Financial Impact Agent:** Simulates Revenue, PBT, Debtor Cycle Savings, and Inventory Reduction. Contains a conflict resolution loop back to Pack Size.
4. **Production Planning Agent:** Simulates EOQ batch sizing, plant utilisation, and "factory issue rate".
5. **Dispatch Optimization Agent:** Uses NetworkX to simulate routing and lead time reductions.

## Known Methodological Problems (To Be Corrected)
1. **Data Architecture:** Naively joining non-related datasets by Date/SKU creates fundamentally invalid synthetic relationships.
2. **Train/Test Split Leakage:** The Demand agent splits the dataset by row index per SKU rather than using a global chronological split.
3. **Model Selection without Baselines:** The Demand agent uses Random Forest without comparing against naive or rolling mean baselines.
4. **Target Clamping (`np.clip`):** The Financial Impact agent and Dispatch Optimization agent artificially force generated outputs to fall within arbitrary pre-defined benchmark ranges (e.g., 20-30% reduction).
5. **LLM/Agent Claims:** The system uses standard deterministic ML classes but describes them as "Joule Agents", "SAP HANA Cloud Vector Engine", etc.
6. **Dashboard Coupling:** The Streamlit UI triggers full model retraining and pipeline runs on execution, rather than reading cached artifacts.
7. **Large Tracked Artifacts:** The `.venv`, pycache, cache models, and massive Jupyter notebook output strings were originally tracked or present.

## Features to Preserve
- The 5-stage conceptual pipeline framework (Demand, Pack Size, Financial, Production, Dispatch).
- The use of the SupplyGraph dataset to model supply chain telemetry.
- Streamlit dashboard visualization concepts (Charts, KPIs, Download tables).
- Pydantic/dataclass-style orchestration flow.

## Features to Remove (And Reason)
- **M5 dataset join:** Completely removed from the repository because joining non-related Walmart retail data with FMCG manufacturing telemetry creates fundamentally invalid synthetic relationships.
- **Target-clamped metrics:** Removed because forcing results to match an external white-paper benchmark invalidates the simulation. Replaced with honest calculation and comparative benchmarking.
- **SAP Fake Connection Toggles:** Removed as they misrepresent the technical reality of the project. Mentioned instead strictly as a "Deployment Blueprint".
- **`np.clip()` constraints in Financial/Dispatch Agents:** Removed to allow raw metrics to surface honestly.
- **Automatic Retraining in Streamlit:** Removed because it causes UX freezes and state-loss. Streamlit now solely serves as a viewer for generated artifacts.
