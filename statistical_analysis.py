"""Compare immune-cell frequencies between miraclib responders and non-responders."""

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy.stats import ttest_ind


ROOT = Path(__file__).resolve().parent
DATABASE_PATH = ROOT / "cell_counts.db"
FREQUENCY_PATH = ROOT / "outputs" / "cell_frequencies.csv"
OUTPUT_DIRECTORY = ROOT / "outputs"
STATISTICS_PATH = OUTPUT_DIRECTORY / "statistical_results.csv"
BOXPLOT_PATH = OUTPUT_DIRECTORY / "responder_boxplots.png"

METADATA_QUERY = """
    SELECT
        samples.sample_name AS sample,
        subjects.subject_id,
        subjects.subject_name AS subject,
        projects.project_name AS project,
        subjects.condition,
        subjects.treatment,
        subjects.response,
        samples.sample_type,
        samples.time_from_treatment_start
    FROM samples
    JOIN subjects
        ON subjects.subject_id = samples.subject_id
    JOIN projects
        ON projects.project_id = subjects.project_id
"""

def load_analysis_data():
    frequencies = pd.read_csv(FREQUENCY_PATH)

    with sqlite3.connect(DATABASE_PATH) as connection:
        metadata = pd.read_sql_query(
            METADATA_QUERY,
            connection,
        )

    combined = frequencies.merge(
        metadata,
        on="sample",
        how="inner",
        validate="many_to_one",
    )

    filtered = combined[
        (combined["condition"] == "melanoma")
        & (combined["treatment"] == "miraclib")
        & (combined["sample_type"] == "PBMC")
        & (combined["response"].isin(["yes", "no"]))
    ].copy()

    subject_means = (
        filtered.groupby(
            [
                "subject_id",
                "subject",
                "response",
                "population",
            ],
            as_index=False,
        )["percentage"]
        .mean()
    )

    return filtered, subject_means

def benjamini_hochberg(p_values):
    """Adjust multiple p-values using the Benjamini-Hochberg procedure."""
    ranked = sorted(
        enumerate(p_values),
        key=lambda item: item[1],
    )

    adjusted = [0.0] * len(p_values)
    total_tests = len(p_values)
    running_minimum = 1.0

    for rank, (original_index, p_value) in reversed(
        list(enumerate(ranked, start=1))
    ):
        corrected_value = p_value * total_tests / rank
        running_minimum = min(running_minimum, corrected_value)
        adjusted[original_index] = min(running_minimum, 1.0)

    return adjusted


def run_statistical_tests(subject_means):
    results = []

    for population in sorted(
        subject_means["population"].unique()
    ):
        population_data = subject_means[
            subject_means["population"] == population
        ]

        responders = population_data.loc[
            population_data["response"] == "yes",
            "percentage",
        ]

        nonresponders = population_data.loc[
            population_data["response"] == "no",
            "percentage",
        ]

        t_statistic, p_value = ttest_ind(
            responders,
            nonresponders,
            equal_var=False,
        )

        results.append(
            {
                "population": population,
                "responder_subjects": len(responders),
                "nonresponder_subjects": len(nonresponders),
                "responder_mean_percentage": responders.mean(),
                "nonresponder_mean_percentage": nonresponders.mean(),
                "mean_difference": (
                    responders.mean() - nonresponders.mean()
                ),
                "t_statistic": t_statistic,
                "p_value": p_value,
            }
        )

    statistics = pd.DataFrame(results)

    statistics["adjusted_p_value"] = benjamini_hochberg(
        statistics["p_value"].tolist()
    )

    statistics["significant"] = (
        statistics["adjusted_p_value"] < 0.05
    )

    return statistics.sort_values(
        "adjusted_p_value"
    ).reset_index(drop=True)

def create_boxplots(subject_means):
    sns.set_theme(style="whitegrid")

    population_order = [
        "b_cell",
        "cd8_t_cell",
        "cd4_t_cell",
        "nk_cell",
        "monocyte",
    ]

    plot = sns.catplot(
        data=subject_means,
        x="response",
        y="percentage",
        hue="response",
        col="population",
        col_order=population_order,
        col_wrap=3,
        kind="box",
        order=["no", "yes"],
        hue_order=["no", "yes"],
        palette={
            "no": "#D95F59",
            "yes": "#2A9D8F",
        },
        sharey=False,
        height=3.5,
        aspect=1.05,
        legend=False,
    )

    plot.set_axis_labels(
        "Treatment response",
        "Relative frequency (%)",
    )
    plot.set_titles("{col_name}")

    plot.figure.subplots_adjust(top=0.86)
    plot.figure.suptitle(
        "Immune Cell Frequencies by Miraclib Response",
        fontsize=14,
    )

    plot.figure.savefig(
        BOXPLOT_PATH,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(plot.figure)

    return BOXPLOT_PATH


if __name__ == "__main__":
    filtered, subject_means = load_analysis_data()
    statistics = run_statistical_tests(subject_means)

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    boxplot_path = create_boxplots(subject_means)

    statistics.to_csv(
        STATISTICS_PATH,
        index=False,
    )

    print(f"Filtered samples: {filtered['sample'].nunique():,}")
    print(f"Unique subjects: {filtered['subject_id'].nunique():,}")
    print()
    print(statistics.to_string(index=False))
    print()
    print(f"Saved statistical results to: {STATISTICS_PATH}")
    print(f"Saved boxplots to: {boxplot_path}")

