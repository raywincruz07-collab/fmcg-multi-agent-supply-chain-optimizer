import pytest
from pathlib import Path
from experiments.m5_forecasting_benchmark import run_m5_benchmark


def test_m5_graceful_exit_without_data(capsys):
    """M5 script must exit gracefully if source data is unavailable."""
    # Running it directly
    with pytest.raises(SystemExit) as exc:
        run_m5_benchmark()

    out, err = capsys.readouterr()
    assert "Skipping benchmark" in out
    # Assuming the raw data isn't there, it should exit and print skipping
    assert "[INFO] M5 dataset not found" in out
