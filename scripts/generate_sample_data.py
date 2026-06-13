import os
from pathlib import Path
import pandas as pd
import numpy as np


def generate_sample_data():
    """Generates a coherent, valid sample dataset for the pipeline."""
    np.random.seed(42)

    # 1. Define entities
    skus = [f"SKU_{i:03d}" for i in range(1, 11)]
    plants = ["P_100", "P_200", "P_300"]
    storage = ["S_10", "S_20", "S_30"]
    product_groups = ["G1", "G2"]

    # 2. Mappings
    # Each SKU maps to exactly one Plant and one Storage Location
    sku_mappings = []
    for i, sku in enumerate(skus):
        sku_mappings.append(
            {
                "SkuId": sku,
                "PlantId": plants[i % len(plants)],
                "StorageLocationId": storage[i % len(storage)],
                "ProductGroup": product_groups[i % len(product_groups)],
            }
        )
    mappings_df = pd.DataFrame(sku_mappings)

    # 3. Graph Connectivity (Edges)
    # Plants -> Storage -> Customers
    edges = []
    for plant in plants:
        for st in storage:
            edges.append({"source": plant, "target": st, "type": "plant_to_storage"})
    for st in storage:
        edges.append({"source": st, "target": "Customer", "type": "storage_to_customer"})
    graph_df = pd.DataFrame(edges)

    # 4. Temporal Fact Table (Date, SkuId)
    # Generate 150 days of data (chronological) to allow train/test splits + lag
    dates = pd.date_range("2023-01-01", periods=150, freq="D")

    facts = []
    for sku in skus:
        # Base demand characteristics per SKU
        base_demand = np.random.uniform(20, 100)
        volatility = np.random.uniform(0.1, 0.5)
        # Introduce zero-demand probability
        zero_prob = np.random.uniform(0.0, 0.3)

        for d in dates:
            if np.random.rand() < zero_prob:
                sales = 0
            else:
                sales = max(0, int(np.random.normal(base_demand, base_demand * volatility)))

            # Production usually matches sales with some variation
            production = int(sales * np.random.uniform(0.9, 1.2)) if sales > 0 else 0

            facts.append(
                {
                    "Date": d.strftime("%Y-%m-%d"),
                    "SkuId": sku,
                    "SalesOrderQty": sales,
                    "ProductionQty": production,
                    "DeliveryQty": sales,
                    "FactoryIssueQty": max(
                        0, int(production * np.random.uniform(0.01, 0.05))
                    ),  # 1-5% of prod
                    "OnHandQty": max(
                        0, int(np.random.normal(base_demand * 1.5, base_demand * 0.2))
                    ),
                    "UnitCost": round(np.random.uniform(10, 50), 2),
                    "Price": round(np.random.uniform(60, 120), 2),
                    "Promotional_Flag": int(np.random.rand() < 0.1),
                }
            )

    fact_df = pd.DataFrame(facts)

    # Output paths
    root = Path(__file__).resolve().parent.parent
    sample_dir = root / "data" / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)

    mappings_df.to_csv(sample_dir / "mappings_sample.csv", index=False)
    graph_df.to_csv(sample_dir / "graph_sample.csv", index=False)
    fact_df.to_csv(sample_dir / "supplygraph_sample.csv", index=False)

    print(f"Sample data generated in {sample_dir}")
    print(f"  Facts: {len(fact_df)} rows")
    print(f"  Mappings: {len(mappings_df)} rows")
    print(f"  Graph: {len(graph_df)} edges")


if __name__ == "__main__":
    generate_sample_data()
