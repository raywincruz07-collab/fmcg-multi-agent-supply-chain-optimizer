# Model Card: FMCG Agentic AI Pipeline

## Model Details
- **Architecture**: Orchestrated pipeline of 5 deterministic agents (Demand, Pack Size, Financial, Production, Dispatch).
- **Date**: 2026-06
- **Version**: 1.0

## Intended Use
- **Primary Use Case**: Demonstrate integration of machine learning and deterministic optimization for FMCG supply chain decision support.
- **Out-of-Scope**: Not intended for autonomous execution or direct supply chain control without human review.

## Data
- **Training Data**: Synthetically generated dataset matching the taxonomy of SupplyGraph (FMCG manufacturing telemetry).
- **Splits**: Strict chronological splitting (Train: Minimum 90 days, Validation: 30 days, Test: 30 days).

## Performance
- **Metrics**: 
  - Demand Forecasting: Evaluated via WAPE, MAE, RMSE, sMAPE on the test set. Model selection is based entirely on validation WAPE.
  - Financials: Explicit Operating Contribution bridge (Revenue vs. COGS, Overhead, Carrying Cost).
- **Fairness & Bias**: Evaluated across SKU segments equally.
