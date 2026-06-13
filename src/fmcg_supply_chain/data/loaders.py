import pandas as pd
from pathlib import Path
from typing import Tuple, Dict


class UnifiedDataLoader:
    """
    Loads SupplyGraph telemetry data and structural mappings.
    Prioritizes raw datasets if available, otherwise falls back to the curated sample.
    """

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.raw_dir = root_dir / "data" / "raw" / "supplygraph"
        self.sample_dir = root_dir / "data" / "sample"

    def _melt_temporal(self, filepath: Path, value_name: str) -> pd.DataFrame:
        """Read a wide-format CSV (rows=dates, cols=SKUs) and melt to long."""
        if not filepath.exists():
            return pd.DataFrame()
        df = pd.read_csv(filepath)
        date_col = df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.rename(columns={date_col: "Date"})
        melted = df.melt(id_vars="Date", var_name="SkuId", value_name=value_name)
        melted[value_name] = pd.to_numeric(melted[value_name], errors="coerce").fillna(0)
        return melted

    def load(self) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        Loads the fact table (Date, SkuId) and dimensional mappings.
        Returns:
            fact_df: A DataFrame where (Date, SkuId) is unique.
            metadata: A dictionary containing structural mapping dataframes.
        """
        # Try raw first
        if (self.raw_dir / "Temporal Data").exists():
            return self._load_raw()
        else:
            return self._load_sample()

    def _load_sample(self) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        fact_df = pd.read_csv(self.sample_dir / "supplygraph_sample.csv")
        fact_df["Date"] = pd.to_datetime(fact_df["Date"])
        mappings = pd.read_csv(self.sample_dir / "mappings_sample.csv")
        graph = pd.read_csv(self.sample_dir / "graph_sample.csv")

        metadata = {"sku_mappings": mappings, "graph_edges": graph}
        return fact_df, metadata

    def _load_raw(self) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        # This implementation assumes standard supplygraph layout.
        # For this refactor we rely on the logic defined in the sample generator,
        # but here we load the wide CSVs into the correct fact grain.
        unit_dir = self.raw_dir / "Temporal Data" / "Unit"

        so = self._melt_temporal(unit_dir / "Sales Order.csv", "SalesOrderQty")
        pr = self._melt_temporal(unit_dir / "Production .csv", "ProductionQty")
        dl = self._melt_temporal(unit_dir / "Delivery To distributor.csv", "DeliveryQty")
        fi = self._melt_temporal(unit_dir / "Factory Issue.csv", "FactoryIssueQty")

        if so.empty:
            raise FileNotFoundError("Raw Sales Order data missing.")

        # Merge on exact grain
        base = so.copy()
        for df, col in [(pr, "ProductionQty"), (dl, "DeliveryQty"), (fi, "FactoryIssueQty")]:
            if not df.empty:
                base = base.merge(df, on=["Date", "SkuId"], how="left")
            else:
                base[col] = 0

        base.fillna(0, inplace=True)

        # We also need mappings and graphs. If they are missing in raw, we return empty structures.
        pd.DataFrame()
        if (self.raw_dir / "Nodes" / "Plant.csv").exists():
            pd.read_csv(self.raw_dir / "Nodes" / "Plant.csv")

        # Normalize and construct dimensions...
        metadata = {
            "sku_mappings": pd.DataFrame(),  # To be populated by raw parser if present
            "graph_edges": pd.DataFrame(),
        }

        return base, metadata


def validate_schema(fact_df: pd.DataFrame, mappings_df: pd.DataFrame) -> bool:
    """Validates uniqueness of temporal fact grain and valid mappings."""
    if fact_df.duplicated(subset=["Date", "SkuId"]).any():
        raise ValueError("Fact table contains duplicate (Date, SkuId) records.")

    if mappings_df.duplicated(subset=["SkuId"]).any():
        raise ValueError("Mappings table contains duplicate SkuId records.")

    return True
