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

def frequency_table() -> pd.DataFrame:
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

    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_style("whitegrid")

    plt.figure(figsize=(12, 8))
    sns.boxplot(x="population", y="percentage", hue="response", data=df)
    plt.title("Cell Population Percentages by Response Status")
    plt.xlabel("Cell Population")
    plt.ylabel("Percentage of Total Cells")
    plt.legend(title="Response")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


