# Methodology

This repository provides a verifiable decision-support system.

1. **Demand Forecasting**: Uses rolling validation to select the best model (Random Forest vs Naive/Rolling/Seasonal baselines). Zero-demand days are treated natively without imputation to preserve true sparsity.
2. **Pack Size Optimization**: Utilizes K-Means clustering on SKU velocity to recommend realistic pack configurations aligned with MOQs.
3. **Financial Impact Analysis**: Computes an exact Operating Contribution bridge without arbitrary clamping or artificial multipliers.
4. **Production Planning**: Outputs Economic Order Quantity (EOQ) batch sizes.
5. **Dispatch Optimization**: Computes deterministic shortest paths using NetworkX, enforcing capacity constraints and network feasibility.

*Note: The M5 dataset has been explicitly excluded from this repository to preserve architectural purity and prevent invalid joins between retail POS data and FMCG telemetry.*
