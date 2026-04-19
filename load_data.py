import sqlite3
import pandas as pd
import os

# Connect to the SQLite database

CSV_PATH = "cell-count.csv"


def create_schema(conn: sqlite3.Connection) -> None:

    """
    Making two tables from cell count data, one for samples and one for cell counts.

    samples which stores all metadata relevant

    cell counts stores the cell count data

    sample_id column will be the key present in both tables we can use to identify as the foreign key.

    """
    conn.executescript(
        """
        -- Drop the tables if they already exist to start fresh
        DROP TABLE IF EXISTS cell_counts;
        DROP TABLE IF EXISTS samples;
 
        -- Metadata table: one row per sample
        CREATE TABLE samples (
            sample_id                   TEXT    PRIMARY KEY,
            project                     TEXT    NOT NULL,
            subject                     TEXT    NOT NULL,
            condition                   TEXT,
            age                         INTEGER,
            sex                         TEXT,
            treatment                   TEXT,
            response                    TEXT,
            sample_type                 TEXT,
            time_from_treatment_start   INTEGER
        );
 
        -- Cell count table: one row per population per sample
        -- References samples via sample_id (foreign key)
        CREATE TABLE cell_counts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_id   TEXT    NOT NULL REFERENCES samples(sample_id),
            population  TEXT    NOT NULL,
            count       INTEGER NOT NULL
        );
 
        -- Index speeds up joins and WHERE filters on sample_id
        CREATE INDEX idx_cell_counts_sample_id ON cell_counts(sample_id);
    """)
    conn.commit()


def load_csv(conn: sqlite3.Connection, csv_path: str) -> None:
    """
    Load data from the CSV file into the database.
    """

    # Read csv file into a pandas dataframe
    df = pd.read_csv(csv_path)

    # Insert metadata into samples table
    # All columns except the populations will be inserted into the samples table

    # Rename sample column to sample_id to match the schema created
    samples_df = df[[
        "sample", "project", "subject", "condition", "age",
        "sex", "treatment", "response", "sample_type",
        "time_from_treatment_start"
    ]].rename(columns={"sample": "sample_id"})


    # Null handling for responses for some samples being replaced
    samples_df["response"] = samples_df["response"].replace("", None)

    # Insert all of it into the samples table
    samples_df.to_sql("samples", conn, if_exists="append", index=False)


    # Insert cell counts into the cell_counts table
    counts_df = df[[
        "sample", "b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"
        ]].rename(columns={"sample": "sample_id"})

    # Use melt to transform into a long format and have sample_id be the identifier
    counts_long = counts_df.melt(
        id_vars="sample_id",
        value_vars=["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"],
        var_name="population",
        value_name="count"
    )
 
    counts_long.to_sql("cell_counts", conn, if_exists="append", index=False)

    print(f"Loaded {len(df)} frames from {csv_path}.")
    print(f"Loaded {len(counts_long)} cell count records.")

def main():
    if os.path.exists("cell_counts.db"):
        os.remove("cell_counts.db")

    conn = sqlite3.connect("cell_counts.db")

    create_schema(conn)

    load_csv(conn, CSV_PATH)

    conn.close()


if __name__ == "__main__":
    main()
