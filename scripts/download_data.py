import os
import sys
from pathlib import Path


def main():
    print("================================================================")
    print("              FMCG Supply Chain Data Setup                      ")
    print("================================================================\n")
    print("This project requires external datasets to run the full pipeline.")
    print("Due to licensing restrictions and repository size limits, raw datasets")
    print("are not included in this repository.\n")
    print("You can run the demo mode using the committed sample dataset without")
    print("downloading these files.\n")

    print("--- 1. SupplyGraph Dataset (Core Requirement) ---")
    print("Reference: Wasi, N., Ahmed, S., & Anwaar, M. (2024).")
    print("           SupplyGraph: A Benchmark Dataset for Supply Chain Planning.")
    print("           Proceedings of the AAAI Workshop on AI for Time Series Analysis (AI4TS).")
    print("License: Please refer to the original authors' repository for licensing.")
    print("Instructions:")
    print("  1. Download the SupplyGraph dataset.")
    print("  2. Place the 'Temporal Data', 'Nodes', and 'Edges' directories inside:")
    print("     data/raw/supplygraph/\n")

    print("--- 2. M5 Forecasting Dataset (Optional Benchmark) ---")
    print("Reference: Makridakis, S., Spiliotis, E., & Assimakopoulos, V. (2020).")
    print("           M5 Competition: Uncertainty Edition. Kaggle.")
    print("License: Public domain / applicable Kaggle competition rules.")
    print("Instructions:")
    print("  1. Download the M5 Forecasting - Accuracy dataset from Kaggle.")
    print("  2. Place 'calendar.csv', 'sales_train_validation.csv', etc. inside:")
    print("     data/raw/m5/\n")

    print("================================================================")

    # Validation step
    root = Path(__file__).resolve().parent.parent
    sg_dir = root / "data" / "raw" / "supplygraph"
    m5_dir = root / "data" / "raw" / "m5"

    missing_critical = False

    print("Checking directories...\n")

    if not (sg_dir / "Temporal Data").exists():
        print("[!] SupplyGraph data is missing or incorrectly placed.")
        missing_critical = True
    else:
        print("[OK] SupplyGraph 'Temporal Data' found.")

    if not (sg_dir / "Nodes").exists():
        print("[!] SupplyGraph 'Nodes' directory is missing.")
        missing_critical = True
    else:
        print("[OK] SupplyGraph 'Nodes' found.")

    if not (m5_dir / "calendar.csv").exists():
        print("[INFO] Optional M5 dataset is missing. The M5 benchmark will not run.")
    else:
        print("[OK] M5 'calendar.csv' found.")

    print("\n================================================================")
    if missing_critical:
        print("STATUS: Missing critical full dataset files.")
        print("You can still run the pipeline using the sample dataset:")
        print("    python scripts/run_pipeline.py --config configs/default.yaml")
        sys.exit(1)
    else:
        print("STATUS: Full datasets verified successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
