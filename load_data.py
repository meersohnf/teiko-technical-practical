import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "cell-count.csv"
DATABASE_PATH = ROOT / "cell_counts.db"

CELL_POPULATIONS = (
    "b_cell",
    "cd8_t_cell",
    "cd4_t_cell",
    "nk_cell",
    "monocyte",
)


def create_database():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    connection.executescript("""
        DROP TABLE IF EXISTS cell_counts;
        DROP TABLE IF EXISTS cell_populations;
        DROP TABLE IF EXISTS samples;
        DROP TABLE IF EXISTS subjects;
        DROP TABLE IF EXISTS projects;

        CREATE TABLE projects (
            project_id INTEGER PRIMARY KEY,
            project_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE subjects (
            subject_id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            subject_name TEXT NOT NULL,
            condition TEXT NOT NULL,
            age INTEGER NOT NULL CHECK (age >= 0),
            sex TEXT NOT NULL,
            treatment TEXT NOT NULL,
            response TEXT CHECK (
                response IS NULL OR response IN ('yes', 'no')
            ),
            FOREIGN KEY (project_id) REFERENCES projects(project_id),
            UNIQUE (project_id, subject_name)
        );

        CREATE TABLE samples (
            sample_id INTEGER PRIMARY KEY,
            sample_name TEXT NOT NULL UNIQUE,
            subject_id INTEGER NOT NULL,
            sample_type TEXT NOT NULL,
            time_from_treatment_start INTEGER NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
        );

        CREATE TABLE cell_populations (
            population_id INTEGER PRIMARY KEY,
            population_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE cell_counts (
            sample_id INTEGER NOT NULL,
            population_id INTEGER NOT NULL,
            cell_count INTEGER NOT NULL CHECK (cell_count >= 0),
            PRIMARY KEY (sample_id, population_id),
            FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
            FOREIGN KEY (population_id)
                REFERENCES cell_populations(population_id)
        );
    """)

    return connection


def load_cell_populations(connection):
    connection.executemany(
        """
        INSERT INTO cell_populations (population_name)
        VALUES (?)
        """,
        [(population,) for population in CELL_POPULATIONS],
    )

    return len(CELL_POPULATIONS)

def read_csv_rows():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")

    with CSV_PATH.open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    if not rows:
        raise ValueError("The CSV file contains no data.")

    return rows

def load_projects(connection, rows):
    project_names = sorted(
        {row["project"].strip() for row in rows}
    )

    connection.executemany(
        """
        INSERT INTO projects (project_name)
        VALUES (?)
        """,
        [(project_name,) for project_name in project_names],
    )

    return dict(
        connection.execute(
            """
            SELECT project_name, project_id
            FROM projects
            """
        ).fetchall()
    )

def load_subjects(connection, rows, project_ids):
    subjects = {}

    for row in rows:
        project_name = row["project"].strip()
        subject_name = row["subject"].strip()
        subject_key = (project_name, subject_name)

        response = row["response"].strip() or None

        subject_record = (
            project_ids[project_name],
            subject_name,
            row["condition"].strip(),
            int(row["age"]),
            row["sex"].strip(),
            row["treatment"].strip(),
            response,
        )

        if (
            subject_key in subjects
            and subjects[subject_key] != subject_record
        ):
            raise ValueError(
                f"Inconsistent metadata for subject: {subject_key}"
            )

        subjects[subject_key] = subject_record

    connection.executemany(
        """
        INSERT INTO subjects (
            project_id,
            subject_name,
            condition,
            age,
            sex,
            treatment,
            response
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        subjects.values(),
    )

    subject_ids = {}

    results = connection.execute(
        """
        SELECT
            projects.project_name,
            subjects.subject_name,
            subjects.subject_id
        FROM subjects
        JOIN projects
            ON projects.project_id = subjects.project_id
        """
    ).fetchall()

    for project_name, subject_name, subject_id in results:
        subject_ids[(project_name, subject_name)] = subject_id

    return subject_ids

def load_samples(connection, rows, subject_ids):
    sample_records = []

    for row in rows:
        subject_key = (
            row["project"].strip(),
            row["subject"].strip(),
        )

        sample_records.append(
            (
                row["sample"].strip(),
                subject_ids[subject_key],
                row["sample_type"].strip(),
                int(row["time_from_treatment_start"]),
            )
        )

    connection.executemany(
        """
        INSERT INTO samples (
            sample_name,
            subject_id,
            sample_type,
            time_from_treatment_start
        )
        VALUES (?, ?, ?, ?)
        """,
        sample_records,
    )

    return dict(
        connection.execute(
            """
            SELECT sample_name, sample_id
            FROM samples
            """
        ).fetchall()
    )


def load_cell_counts(connection, rows, sample_ids):
    population_ids = dict(
        connection.execute(
            """
            SELECT population_name, population_id
            FROM cell_populations
            """
        ).fetchall()
    )

    cell_count_records = []

    for row in rows:
        sample_id = sample_ids[row["sample"].strip()]

        for population in CELL_POPULATIONS:
            count = int(row[population])

            if count < 0:
                raise ValueError(
                    f"Negative count for {population} "
                    f"in sample {row['sample']}"
                )

            cell_count_records.append(
                (
                    sample_id,
                    population_ids[population],
                    count,
                )
            )

    connection.executemany(
        """
        INSERT INTO cell_counts (
            sample_id,
            population_id,
            cell_count
        )
        VALUES (?, ?, ?)
        """,
        cell_count_records,
    )

    return len(cell_count_records)


def verify_database(connection, expected_samples):
    expected_counts = {
        "projects": 3,
        "subjects": 3500,
        "samples": expected_samples,
        "cell_populations": len(CELL_POPULATIONS),
        "cell_counts": expected_samples * len(CELL_POPULATIONS),
    }

    for table_name, expected_count in expected_counts.items():
        actual_count = connection.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]

        if actual_count != expected_count:
            raise RuntimeError(
                f"{table_name}: expected {expected_count}, "
                f"but found {actual_count}"
            )

    incomplete_samples = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT sample_id
            FROM cell_counts
            GROUP BY sample_id
            HAVING COUNT(*) != ?
        )
        """,
        (len(CELL_POPULATIONS),),
    ).fetchone()[0]

    if incomplete_samples:
        raise RuntimeError(
            f"{incomplete_samples} samples have incomplete cell counts."
        )

    foreign_key_errors = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if foreign_key_errors:
        raise RuntimeError(
            f"Foreign-key errors found: {foreign_key_errors}"
        )

if __name__ == "__main__":
    rows = read_csv_rows()
    connection = create_database()

    try:
        with connection:
            population_count = load_cell_populations(connection)
            project_ids = load_projects(connection, rows)
            subject_ids = load_subjects(
                connection,
                rows,
                project_ids,
            )
            sample_ids = load_samples(
                connection,
                rows,
                subject_ids,
            )
            cell_count_total = load_cell_counts(
                connection,
                rows,
                sample_ids,
            )
            verify_database(connection, len(rows))
    finally:
        connection.close()

    print(f"Read {len(rows):,} CSV rows.")
    print(f"Loaded {population_count} cell populations.")
    print(f"Loaded {len(project_ids)} projects.")
    print(f"Loaded {len(subject_ids):,} subjects.")
    print(f"Loaded {len(sample_ids):,} samples.")
    print(f"Loaded {cell_count_total:,} cell-count records.")
    print("Database verification passed.")
