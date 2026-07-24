# Miraclib Immune Cell Analysis

Python and SQLite pipeline for analyzing immune-cell populations in clinical trial samples. The project includes database creation, relative-frequency calculations, statistical testing, baseline subset analysis, and an interactive Streamlit dashboard.

## Dashboard

The deployed dashboard URL will be added here after deployment.

## Running the Project

This project requires Python 3.10 or newer.

### Install dependencies

```bash
make setup
```

### Run the complete pipeline

```bash
make pipeline
```

This command:

1. Creates and loads the SQLite database.
2. Calculates cell-population relative frequencies.
3. Performs the responder versus non-responder analysis.
4. Generates statistical results, boxplots, and baseline summaries.

### Start the dashboard

```bash
make dashboard
```

## Database Schema

The SQLite database uses five normalized tables:

- `projects`: Stores each clinical project.
- `subjects`: Stores subject-level information, including condition, age, sex, treatment, and response.
- `samples`: Stores biological samples and their collection timepoints.
- `cell_populations`: Stores the five immune-cell population names.
- `cell_counts`: Connects samples with cell populations and stores each count.

The relationships are:

- One project can contain many subjects.
- One subject can have many samples.
- Each sample can contain counts for multiple cell populations.
- The `cell_counts` table implements the relationship between samples and populations.

This normalized design prevents repeated project, subject, and population information. It also allows additional projects, subjects, samples, timepoints, and cell populations to be added without restructuring the database. Analytical queries can filter metadata independently while joining only the necessary tables.

## Code Structure

- `load_data.py`: Creates the database schema and loads `cell-count.csv`.
- `analysis.py`: Calculates the relative frequency of each cell population in every sample.
- `statistical_analysis.py`: Compares responders and non-responders and generates boxplots.
- `subset_analysis.py`: Produces the baseline melanoma PBMC subset and associated summaries.
- `dashboard.py`: Runs the interactive Streamlit dashboard.
- `Makefile`: Automates dependency installation, pipeline execution, and dashboard startup.
- `outputs/`: Contains generated tables and plots.

## Statistical Analysis

The response analysis includes melanoma patients receiving miraclib with PBMC samples and known response values.

Repeated samples from the same subject were summarized using the subject's mean relative frequency for each cell population. Responders and non-responders were compared using Welch's independent-samples t-test. Benjamini-Hochberg correction was applied across the five cell-population tests.

CD4 T cells were significantly higher in responders:

- Responder mean: 30.54%
- Non-responder mean: 29.90%
- Mean difference: 0.64 percentage points
- Raw p-value: 0.0045
- Adjusted p-value: 0.0226

No other cell population was significant after multiple-testing correction.

## Baseline Analysis

The baseline subset contains melanoma PBMC samples collected at time zero from subjects receiving miraclib.

- Total samples: 656
- Project `prj1`: 384 samples
- Project `prj3`: 272 samples
- Responders: 331 subjects
- Non-responders: 325 subjects
- Female subjects: 312
- Male subjects: 344

Among male melanoma responders at time zero across all sample and treatment types, the average B-cell count was **10,206.15**.

## Generated Outputs

The pipeline generates:

- `cell_counts.db`
- `outputs/cell_frequencies.csv`
- `outputs/statistical_results.csv`
- `outputs/responder_boxplots.png`
- `outputs/baseline_melanoma_pbmc.csv`
- `outputs/baseline_summary.csv`
- `outputs/average_b_cells.csv`