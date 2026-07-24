from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px


ROOT = Path(__file__).resolve().parent
OUTPUT_DIRECTORY = ROOT / "outputs"

FREQUENCY_PATH = OUTPUT_DIRECTORY / "cell_frequencies.csv"
STATISTICS_PATH = OUTPUT_DIRECTORY / "statistical_results.csv"
BASELINE_PATH = OUTPUT_DIRECTORY / "baseline_melanoma_pbmc.csv"
SUMMARY_PATH = OUTPUT_DIRECTORY / "baseline_summary.csv"
AVERAGE_PATH = OUTPUT_DIRECTORY / "average_b_cells.csv"
BOXPLOT_PATH = OUTPUT_DIRECTORY / "responder_boxplots.png"


st.set_page_config(
    page_title="Miraclib Immune Analysis",
    page_icon="🧬",
    layout="wide",
)


@st.cache_data
def load_outputs():
    frequencies = pd.read_csv(FREQUENCY_PATH)
    statistics = pd.read_csv(STATISTICS_PATH)
    baseline = pd.read_csv(BASELINE_PATH)
    baseline_summary = pd.read_csv(SUMMARY_PATH)
    average = pd.read_csv(AVERAGE_PATH)

    return (
        frequencies,
        statistics,
        baseline,
        baseline_summary,
        average,
    )


(
    frequencies,
    statistics,
    baseline,
    baseline_summary,
    average,
) = load_outputs()


st.title("Miraclib Immune Cell Analysis")
st.write(
    "Interactive analysis of immune-cell populations, "
    "treatment response, and baseline samples."
)

column1, column2, column3, column4 = st.columns(4)

column1.metric(
    "Samples",
    f"{frequencies['sample'].nunique():,}",
)

column2.metric(
    "Cell populations",
    frequencies["population"].nunique(),
)

column3.metric(
    "Frequency records",
    f"{len(frequencies):,}",
)

column4.metric(
    "Baseline samples",
    f"{baseline['sample'].nunique():,}",
)

st.divider()

overview_tab, response_tab, baseline_tab = st.tabs(
    [
        "Sample Frequencies",
        "Response Analysis",
        "Baseline Analysis",
    ]
)


with overview_tab:
    st.subheader("Cell Frequencies by Sample")

    selected_sample = st.selectbox(
        "Select a sample",
        sorted(frequencies["sample"].unique()),
    )

    sample_data = frequencies[
        frequencies["sample"] == selected_sample
    ].copy()

    st.metric(
        "Total cells",
        f"{int(sample_data['total_count'].iloc[0]):,}",
    )

    frequency_figure = px.bar(
        sample_data,
        x="population",
        y="percentage",
        color="population",
        text="percentage",
        labels={
            "population": "Cell population",
            "percentage": "Relative frequency (%)",
        },
        title=f"Cell Frequencies for {selected_sample}",
    )

    frequency_figure.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="outside",
    )
    frequency_figure.update_layout(
        showlegend=False,
    )

    st.plotly_chart(
        frequency_figure,
        width="stretch",
    )

    st.dataframe(
        sample_data,
        hide_index=True,
        width="stretch",
    )


with response_tab:
    st.subheader("Miraclib Response Analysis")

    st.write(
        "Melanoma patients receiving miraclib were compared "
        "using subject-level mean frequencies from PBMC samples."
    )

    st.image(
        str(BOXPLOT_PATH),
        width="stretch",
    )

    st.dataframe(
        statistics,
        hide_index=True,
        width="stretch",
    )

    st.success(
        "CD4 T cells were significantly higher in responders "
        "after multiple-testing correction "
        "(adjusted p-value = 0.0226)."
    )


with baseline_tab:
    st.subheader("Baseline Melanoma PBMC Samples")

    baseline_column1, baseline_column2 = st.columns(2)

    baseline_column1.metric(
        "Baseline samples",
        f"{baseline['sample'].nunique():,}",
    )

    baseline_column2.metric(
        "Average B cells in male responders",
        f"{average['average_b_cells'].iloc[0]:,.2f}",
    )

    st.dataframe(
        baseline_summary,
        hide_index=True,
        width="stretch",
    )

    with st.expander("View baseline samples"):
        st.dataframe(
            baseline,
            hide_index=True,
            width="stretch",
        )