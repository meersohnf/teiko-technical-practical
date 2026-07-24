"""Calculate and export cell-population relative frequencies for each sample."""

import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATABASE_PATH = ROOT / "cell_counts.db"
OUTPUT_DIRECTORY = ROOT / "outputs"
SUMMARY_PATH = OUTPUT_DIRECTORY / "cell_frequencies.csv"

FREQUENCY_QUERY = """
    WITH sample_totals AS (
        SELECT
            sample_id,
            SUM(cell_count) AS total_count
        FROM cell_counts
        GROUP BY sample_id
    )
    SELECT
        samples.sample_name AS sample,
        sample_totals.total_count AS total_count,
        cell_populations.population_name AS population,
        cell_counts.cell_count AS count,
        ROUND(
            100.0 * cell_counts.cell_count
            / sample_totals.total_count,
            6
        ) AS percentage
    FROM cell_counts
    JOIN samples
        ON samples.sample_id = cell_counts.sample_id
    JOIN cell_populations
        ON cell_populations.population_id =
           cell_counts.population_id
    JOIN sample_totals
        ON sample_totals.sample_id = samples.sample_id
    ORDER BY
        samples.sample_name,
        cell_populations.population_id
"""


def calculate_frequencies():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}"
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        cursor = connection.execute(FREQUENCY_QUERY)
        columns = [
            description[0]
            for description in cursor.description
        ]
        rows = cursor.fetchall()

    return columns, rows
def write_frequency_summary(columns, rows):
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)

    with SUMMARY_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as output_file:
        writer = csv.writer(output_file)
        writer.writerow(columns)
        writer.writerows(rows)

    return SUMMARY_PATH


if __name__ == "__main__":
    columns, rows = calculate_frequencies()
    summary_path = write_frequency_summary(columns, rows)

    print(columns)

    for row in rows[:5]:
        print(row)

    print(f"Generated {len(rows):,} frequency rows.")
    print(f"Saved summary table to: {summary_path}")