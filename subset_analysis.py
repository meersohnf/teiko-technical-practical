"""Generate baseline melanoma summaries and the requested B-cell average."""

import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATABASE_PATH = ROOT / "cell_counts.db"
OUTPUT_DIRECTORY = ROOT / "outputs"
BASELINE_PATH = OUTPUT_DIRECTORY / "baseline_melanoma_pbmc.csv"
SUMMARY_PATH = OUTPUT_DIRECTORY / "baseline_summary.csv"
AVERAGE_PATH = OUTPUT_DIRECTORY / "average_b_cells.csv"

AVERAGE_B_CELL_QUERY = """
    SELECT
        ROUND(AVG(cell_counts.cell_count), 2)
    FROM cell_counts
    JOIN cell_populations
        ON cell_populations.population_id =
           cell_counts.population_id
    JOIN samples
        ON samples.sample_id = cell_counts.sample_id
    JOIN subjects
        ON subjects.subject_id = samples.subject_id
    WHERE subjects.condition = 'melanoma'
        AND subjects.sex = 'M'
        AND subjects.response = 'yes'
        AND samples.time_from_treatment_start = 0
        AND cell_populations.population_name = 'b_cell'
"""

BASELINE_QUERY = """
    SELECT
        projects.project_name AS project,
        subjects.subject_id,
        subjects.subject_name AS subject,
        subjects.condition,
        subjects.age,
        subjects.sex,
        subjects.treatment,
        subjects.response,
        samples.sample_name AS sample,
        samples.sample_type,
        samples.time_from_treatment_start
    FROM samples
    JOIN subjects
        ON subjects.subject_id = samples.subject_id
    JOIN projects
        ON projects.project_id = subjects.project_id
    WHERE subjects.condition = 'melanoma'
        AND subjects.treatment = 'miraclib'
        AND samples.sample_type = 'PBMC'
        AND samples.time_from_treatment_start = 0
    ORDER BY
        projects.project_name,
        subjects.subject_name
"""


def load_baseline_samples():
    with sqlite3.connect(DATABASE_PATH) as connection:
        baseline = pd.read_sql_query(
            BASELINE_QUERY,
            connection,
        )

    return baseline


def summarize_baseline(baseline):
    unique_subjects = baseline.drop_duplicates(
        subset="subject_id"
    )

    records = []

    project_counts = (
        baseline.groupby("project")["sample"].nunique()
    )

    for project, count in project_counts.items():
        records.append(
            {
                "category": "project",
                "value": project,
                "count_type": "samples",
                "count": count,
            }
        )

    response_counts = (
        unique_subjects.groupby("response")["subject_id"].nunique()
    )

    for response, count in response_counts.items():
        records.append(
            {
                "category": "response",
                "value": response,
                "count_type": "subjects",
                "count": count,
            }
        )

    sex_counts = (
        unique_subjects.groupby("sex")["subject_id"].nunique()
    )

    for sex, count in sex_counts.items():
        records.append(
            {
                "category": "sex",
                "value": sex,
                "count_type": "subjects",
                "count": count,
            }
        )

    return pd.DataFrame(records)

def calculate_average_b_cells():
    with sqlite3.connect(DATABASE_PATH) as connection:
        result = connection.execute(
            AVERAGE_B_CELL_QUERY
        ).fetchone()

    if result is None or result[0] is None:
        raise RuntimeError("No matching B-cell records found.")

    return float(result[0])


if __name__ == "__main__":
    baseline = load_baseline_samples()
    summary = summarize_baseline(baseline)

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    baseline.to_csv(
        BASELINE_PATH,
        index=False,
    )
    summary.to_csv(
        SUMMARY_PATH,
        index=False,
    )
    average_b_cells = calculate_average_b_cells()

    average_result = pd.DataFrame(
        [
            {
                "condition": "melanoma",
                "sex": "M",
                "response": "yes",
                "time_from_treatment_start": 0,
                "sample_type": "all",
                "treatment": "all",
                "average_b_cells": average_b_cells,
            }
        ]
    )

    average_result.to_csv(
        AVERAGE_PATH,
        index=False,
    )

    print(f"Baseline samples: {baseline['sample'].nunique():,}")
    print(f"Baseline subjects: {baseline['subject_id'].nunique():,}")
    print(f"Saved baseline data to: {BASELINE_PATH}")
    print()
    print(summary.to_string(index=False))
    print(f"Saved baseline summary to: {SUMMARY_PATH}")
    print(f"Average B cells: {average_b_cells:.2f}")
    print(f"Saved B-cell average to: {AVERAGE_PATH}")