import sqlite3
import pandas as pd
import os
import scipy.stats as stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots



DB_PATH = "cell_counts.db"
OUTPUT_DIR  = "outputs"
POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

def get_connection() -> sqlite3.Connection:

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def get_frequency_table() -> pd.DataFrame:
    """
    Generate a frequency table of the cell populations across all samples.
    
    """

    sql = """
        SELECT
            cc.sample_id          AS sample,
            cc.population,
            cc.count,
            SUM(cc.count) OVER (PARTITION BY cc.sample_id) AS total_count
        FROM cell_counts cc
        ORDER BY cc.sample_id, cc.population
    """

    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()

    # Calculate percentage of each population within each sample using total count

    df["percentage"] = (df["count"] / df["total_count"] * 100).round(4)

    # Return frequency table in the order specified

    return df[["sample", "total_count", "population", "count", "percentage"]]

def get_responder_data() -> pd.DataFrame:
    """
    Get the responder data for all samples.
    """

    sql = """
        SELECT
            cc.sample_id,
            s.response,
            cc.population,
            cc.count,
            SUM(cc.count) OVER (PARTITION BY cc.sample_id) AS total_count
        FROM cell_counts cc
        JOIN samples s ON cc.sample_id = s.sample_id
        WHERE s.condition   = 'melanoma'
          AND s.treatment   = 'miraclib'
          AND s.sample_type = 'PBMC'
          AND s.response    IN ('yes', 'no')
        ORDER BY cc.sample_id
    """

    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()


    df["percentage"] = (df["count"] / df["total_count"] * 100).round(4)


    return df


def statistics_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Need to compare responders vs non responders for each cell population. Run a Man-Whitnney U test for each population.
    """

    # Store results in a list 
    results = []

    for pop in POPULATIONS:
        # Subset data for the current population for responders and non responders
        pop_df = df[df["population"] == pop]

        # Get percentage values for yes and no, NULL does not count as a response so we ignore it
        responders = pop_df[pop_df["response"] == "yes"]["percentage"]
        non_responders = pop_df[pop_df["response"] == "no"]["percentage"]


        # Perform Mann-Whitney U test and grab the U statistic and p-value
        u_stat, p_value = stats.mannwhitneyu(
            responders, non_responders, alternative="two-sided"
        )

        # Append the results to the list as a dictionary
        results.append({
            "population":  pop,
            "u_statistic": round(u_stat, 4),
            "p_value":     round(p_value, 6),
            "significant": "YES" if p_value < 0.05 else "no"
        })

    return pd.DataFrame(results).sort_values("p_value")
    
def make_boxplot(df: pd.DataFrame) -> None:
    """
    Create boxplots for each population comparing responders vs non responders.
    """
    fig = make_subplots(
        rows=1, cols=len(POPULATIONS),
        subplot_titles=[p.replace("_", " ").title() for p in POPULATIONS],
        shared_yaxes=True
    )


    colors = {"yes": "green", "no": "red"}
    labels = {"yes": "Responder", "no": "Non-Responder"}

    for i, pop in enumerate(POPULATIONS, start=1):
        pop_df = df[df["population"] == pop]
        for response_val in ["yes", "no"]:
            # Make a subset of the data for current population and response value
            subset = pop_df[pop_df["response"] == response_val]["percentage"]
            # Add a box trace to the figure for current population and response value
            fig.add_trace(
                go.Box(
                    y=subset,
                    name=labels[response_val],
                    marker_color=colors[response_val],
                    showlegend=(i == 1),
                    legendgroup=response_val,
                    boxpoints="all",
                    jitter=0.3,
                    pointpos=-1.8
                ),
                row=1, col=i
            )
    fig.update_layout(
        title="Cell Population: Responders vs Non-Responders",
        yaxis_title="Relative Frequency (%)",
        height=550,
        template="plotly_white",
        legend=dict(title="Response")
    )

    return fig


def get_baseline_PBMC() -> pd.DataFrame:
    """
    """

    sql = """
        SELECT s.*
        FROM samples s
        WHERE s.condition = 'melanoma'
            AND s.treatment = 'miraclib'
            AND s.sample_type = 'PBMC'
            AND s.time_from_treatment_start = 0
    """

    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def get_samples_per_project() -> pd.DataFrame:
    # Find how many baseline samples come from each project
    sql = """
        SELECT project, COUNT(*) as sample_count
        FROM samples
        WHERE condition = 'melanoma'
            AND treatment = 'miraclib'
            AND sample_type = 'PBMC'
            AND time_from_treatment_start = 0
        GROUP BY project
    """
    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def responders_non_responders() -> pd.DataFrame:
    # Find the number of responders and non-responders for each project
    sql = """
        SELECT response, COUNT(DISTINCT subject) as subject_count
        FROM samples
        WHERE condition = 'melanoma'
            AND treatment = 'miraclib'
            AND sample_type = 'PBMC'
            AND time_from_treatment_start = 0
            AND response IN ('yes', 'no')
        GROUP BY response
    """
    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def males_females() -> pd.DataFrame:
    # Group by sex and count unique subjects in each group to get the number
    sql = """
        SELECT sex, COUNT(DISTINCT subject) as subject_count
        FROM samples
        WHERE condition = 'melanoma'
            AND treatment = 'miraclib'
            AND sample_type = 'PBMC'
            AND time_from_treatment_start = 0
        GROUP BY sex
    """
    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def avg_number_B_cells() -> float:
    # Calculate the average number of B cells in the baseline time = 0
    sql = """
        SELECT ROUND(AVG(cc.count), 2) AS avg_b_cell
        FROM cell_counts cc
        JOIN samples s ON cc.sample_id = s.sample_id
        WHERE s.condition                 = 'melanoma'
          AND s.treatment                 = 'miraclib'
          AND s.sample_type               = 'PBMC'
          AND s.time_from_treatment_start = 0
          AND s.sex                       = 'M'
          AND s.response                  = 'yes'
          AND cc.population               = 'b_cell'
    """
    conn = get_connection()
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df["avg_b_cell"].iloc[0]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    freq_df = get_frequency_table()
    freq_df.to_csv(f"{OUTPUT_DIR}/frequency_table.csv", index=False)
    print("Frequency table saved")

    resp_df   = get_responder_data()
    stats_df  = statistics_analysis(resp_df)
    stats_df.to_csv(f"{OUTPUT_DIR}/stats_results.csv", index=False)
    print("Stats saved")
    print(stats_df.to_string(index=False))

    fig = make_boxplot(resp_df)
    fig.write_html(f"{OUTPUT_DIR}/boxplot_responders.html")
    print("Boxplot saved")

    proj_df    = get_samples_per_project()
    resp_df2   = responders_non_responders()
    gender_df  = males_females()
    avg_bcell  = avg_number_B_cells()

    summary = f"""
        PART 4 RESULTS
        ---
        Samples per project: {proj_df.to_string(index=False)}

        Responders vs Non-Responders: {resp_df2.to_string(index=False)}

        Males vs Females: {gender_df.to_string(index=False)}

        Avg B cells (melanoma male responders, time=0): {avg_bcell}
        """
    print(summary)
    with open(f"{OUTPUT_DIR}/part4_summary.txt", "w") as f:
        f.write(summary)


if __name__ == "__main__":
    main()