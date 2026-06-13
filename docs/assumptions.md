# Financial and Operational Assumptions

## Financial Scenarios
1. **Base (Neutral) Scenario**: 
   - No demand uplift (0%).
   - No stockout recovery.
   - No pack revenue impact or consolidation benefit.
   - Result: Operating Contribution equals Baseline.
2. **Optimistic/Conservative Scenarios**: Configurable via `configs/default.yaml`.

## Key Formulas
- **Baseline Operating Contribution** = Baseline Revenue - (COGS + Overhead + Carrying Cost)
- **Scenario Operating Contribution** = Scenario Revenue - (Scenario COGS + Overhead + Carrying Cost)
- **Carrying Cost** assumes cycle stock is half the recommended pack size.

## Routing
- Evaluates candidate routes up to `max_route_hops`.
- Assumes routes with capacity <= 50 are infeasible for standard demonstration flows.
