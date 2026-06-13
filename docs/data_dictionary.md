# Data Dictionary

## SupplyGraph Telemetry (Fact Table)
- **Date**: ISO Date of observation.
- **SkuId**: Unique item identifier.
- **SalesOrderQty**: Daily demand/orders.
- **ProductionQty**: Daily manufacturing output.
- **OnHandQty**: Closing stock level.
- **UnitCost**: Manufacturing/purchase cost per unit.
- **Price**: Retail/wholesale selling price.
- **Promotional_Flag**: Binary indicator of active promotions.

## Output Artifacts
- **forecast_df.csv**: SKU-level chronological predictions with confidence intervals.
- **financial_table_df.csv**: Itemized Operating Contribution bridge by SKU.
- **path_df.csv**: Selected dispatch routes with feasibility validation.
