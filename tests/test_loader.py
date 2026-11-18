"""Integration tests for the data loader."""

from pathlib import Path

from scripts.load_data import load_data


def test_loader_idempotency_and_count() -> None:
    csv_path = Path("data/coffee_health_raw.csv")
    stats = load_data(csv_path, batch_size=1000, verbose=False)

    # When run again, it should load 0 new rows (idempotent)
    assert stats.total_read == 10012
    assert stats.loaded == 0
    assert stats.rejected == 25
    assert stats.exact_duplicates == 8
    assert stats.conflicting_duplicates == 4
