"""Load the coffee health CSV into PostgreSQL.

Usage:
    uv run python scripts/load_data.py data/coffee_health_raw.csv
"""

import argparse
import csv
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Ensure workspace root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import psycopg  # noqa: E402
from psycopg.rows import tuple_row  # noqa: E402

from app.config import settings  # noqa: E402
from app.domain.models import CoffeeRecord  # noqa: E402
from scripts.data_cleaner import ValidationResult, clean_and_validate_row  # noqa: E402

INSERT_SQL = """
INSERT INTO public.coffee_records (
    id, age, gender, country, coffee_intake, caffeine_mg,
    sleep_hours, sleep_quality, bmi, heart_rate, stress_level,
    physical_activity_hours, health_issues, occupation,
    smoking, alcohol_consumption
) VALUES (
    %(id)s, %(age)s, %(gender)s, %(country)s, %(coffee_intake)s, %(caffeine_mg)s,
    %(sleep_hours)s, %(sleep_quality)s, %(bmi)s, %(heart_rate)s, %(stress_level)s,
    %(physical_activity_hours)s, %(health_issues)s, %(occupation)s,
    %(smoking)s, %(alcohol_consumption)s
)
ON CONFLICT (id) DO NOTHING;
"""


@dataclass
class IngestionStats:
    total_read: int = 0
    loaded: int = 0
    normalized_fixed: int = 0
    rejected: int = 0
    exact_duplicates: int = 0
    conflicting_duplicates: int = 0

    @property
    def total_duplicates(self) -> int:
        return self.exact_duplicates + self.conflicting_duplicates


def record_to_dict(r: CoffeeRecord) -> dict[str, Any]:
    return {
        "id": r.id,
        "age": r.age,
        "gender": r.gender.value,
        "country": r.country,
        "coffee_intake": r.coffee_intake,
        "caffeine_mg": r.caffeine_mg,
        "sleep_hours": r.sleep_hours,
        "sleep_quality": r.sleep_quality.value,
        "bmi": r.bmi,
        "heart_rate": r.heart_rate,
        "stress_level": r.stress_level.value,
        "physical_activity_hours": r.physical_activity_hours,
        "health_issues": r.health_issues.value,
        "occupation": r.occupation.value,
        "smoking": r.smoking,
        "alcohol_consumption": r.alcohol_consumption,
    }


def chunked(iterable: Iterator[CoffeeRecord], batch_size: int) -> Iterator[list[CoffeeRecord]]:
    """Yield successive batches of records from an iterator to prevent high memory usage."""
    batch: list[CoffeeRecord] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def process_csv(
    csv_path: Path,
    stats: IngestionStats,
    rejections: list[ValidationResult],
) -> Iterator[CoffeeRecord]:
    """Parse, clean and yield valid records while tracking rejections and duplicates."""
    seen_records: dict[int, CoffeeRecord] = {}

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_number, raw_row in enumerate(reader, start=2):
            stats.total_read += 1
            result = clean_and_validate_row(raw_row, line_number)

            if not result.is_valid or result.record is None:
                stats.rejected += 1
                rejections.append(result)
                continue

            record = result.record
            if result.was_fixed:
                stats.normalized_fixed += 1

            # Handle duplicate ID policies
            if record.id in seen_records:
                existing = seen_records[record.id]
                if existing == record:
                    stats.exact_duplicates += 1
                else:
                    stats.conflicting_duplicates += 1
                    rejections.append(
                        ValidationResult(
                            record=None,
                            line_number=line_number,
                            raw_id=str(record.id),
                            was_fixed=False,
                            rejection_reasons=[
                                f"conflicting_duplicate: ID {record.id} already exists"
                            ],
                        )
                    )
                continue

            seen_records[record.id] = record
            yield record


def load_data(
    csv_path: Path,
    database_url: str = settings.database_url,
    batch_size: int = 1000,
    verbose: bool = True,
) -> IngestionStats:
    stats = IngestionStats()
    rejections: list[ValidationResult] = []

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found at: {csv_path}")

    # Count rows in DB before load to determine actually inserted rows
    with psycopg.connect(database_url, row_factory=tuple_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.coffee_records;")
            count_before: int = cur.fetchone()[0]  # type: ignore[index]

        # Generator pipeline for streaming chunked insertion
        record_generator = process_csv(csv_path, stats, rejections)

        with conn.cursor() as cur:
            for batch in chunked(record_generator, batch_size):
                dicts = [record_to_dict(r) for r in batch]
                cur.executemany(INSERT_SQL, dicts)
            conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.coffee_records;")
            count_after: int = cur.fetchone()[0]  # type: ignore[index]

    stats.loaded = count_after - count_before

    if verbose:
        print_summary(stats, rejections, count_after)

    return stats


def print_summary(
    stats: IngestionStats,
    rejections: list[ValidationResult],
    total_in_db: int,
) -> None:
    print("=" * 70)
    print("COFFEE HEALTH INGESTION REPORT")
    print("=" * 70)
    print(f"Rows read from CSV:         {stats.total_read:>6}")
    print(f"Rows newly loaded:          {stats.loaded:>6}")
    print(f"Total rows now in database: {total_in_db:>6}")
    print(f"Rows normalized/fixed:      {stats.normalized_fixed:>6}")
    print(f"Rows rejected:              {stats.rejected:>6}")
    print(f"Duplicate IDs:              {stats.total_duplicates:>6}")
    print(f"  - Exact duplicates:       {stats.exact_duplicates:>6}")
    print(f"  - Conflicting duplicates: {stats.conflicting_duplicates:>6}")
    print("=" * 70)

    if rejections:
        print("\nSAMPLE REJECTED ROWS (Line # | Raw ID | Reason):")
        print("-" * 70)
        for r in rejections[:30]:
            reasons_str = "; ".join(r.rejection_reasons)
            print(f"Line {r.line_number:>5} | ID: {str(r.raw_id):>5} | {reasons_str}")
        if len(rejections) > 30:
            print(f"... and {len(rejections) - 30} more rejections.")
        print("-" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="Path to raw coffee health CSV")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for database insertions (default: 1000)",
    )
    args = parser.parse_args()

    try:
        load_data(args.csv_path, batch_size=args.batch_size)
    except Exception as e:
        print(f"Error loading data: {e}", file=sys.stderr)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
