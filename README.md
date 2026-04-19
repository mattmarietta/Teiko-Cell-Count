# Teiko-Cell-Count

Clinical trial dashboard analyzing how miraclib affects immune cell populations across patient samples.

---

## How to Run

### Using GitHub Codespaces
```bash
make setup      # install dependencies
make pipeline   # load data + run all analysis
make dashboard  # start dashboard at http://localhost:8050
```

### Manually
```bash
pip install -r requirements.txt
python load_data.py   # creates cell_counts.db
python analysis.py    # creates outputs/
python dashboard.py   # serves dashboard
```

---

## Project Structure

```
.
├── load_data.py          Loads CSV into SQLite
├── analysis.py           All analysis logic
├── dashboard.py          Interactive Dash dashboard
├── cell-count.csv        Input data
├── cell_counts.db        Generated SQLite database (after pipeline)
├── outputs/
│   ├── frequency_table.csv       Part 2 output
│   ├── stats_results.csv         Part 3 statistical results
│   ├── boxplot_responders.html   Part 3 visualization
│   └── part4_summary.txt         Part 4 answers
├── requirements.txt              Python modules
├── Makefile 
└── README.md
```

### Why it's structured this way

- `load_data.py` is isolated so it can be run independently and re-run to reset the DB, kept lightweight on purpose.
- `analysis.py` contains all query + computation logic as importable functions so the dashboard imports them directly rather than duplicating code across multiple files.
- `dashboard.py` is purely UI layer; it calls analysis functions and renders results. Much of the code is followed from examples found online to make an easily readable dashboard using dash and plotly.

---

## Database Schema

```sql
CREATE TABLE samples (
    sample_id                   TEXT    PRIMARY KEY,
    project                     TEXT,
    subject                     TEXT,
    condition                   TEXT,
    age                         INTEGER,
    sex                         TEXT,
    treatment                   TEXT,
    response                    TEXT,
    sample_type                 TEXT,
    time_from_treatment_start   INTEGER
);

CREATE TABLE cell_counts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id   TEXT    REFERENCES samples(sample_id),
    population  TEXT,
    count       INTEGER
);
```

### Design Rationale

The source CSV is very wide with five cell count columns alongside repeated metadata. Normalizing this data into two tables eliminates redundancy because patient metadata is stored once per sample in `samples`, while `cell_counts` holds one row per (sample × population) pair. This is a standard pattern where `samples` acts as the dimension table and `cell_counts` as the fact table.

**How this scales:**
- **Hundreds of projects**: `project` is a column, not a separate table. At large scale, you'd promote it to its own `projects` table and join, there would be no need for a schema change to existing tables.
- **Thousands of samples**: The `cell_counts` table grows at 5× the sample count (one row per population). With an index on `sample_id`, queries would still remain fast with millions of rows.
- **New cell populations**: Adding a new population like `example_cell` is just new rows in `cell_counts`. There would be no column additions or migrations needed.
- **New analytics**: Since data is normalized, you can slice by any combination of metadata (`condition`, `treatment`, `sex`, `time_from_treatment_start`) with simple WHERE clauses and window functions within SQL or python.

---

## Statistical Approach (Part 3)

Mann-Whitney U test was chosen over a standard t-test because:
1. Cell percentage distributions are often skewed in clinical data
2. Sample sizes per group can be small
3. It requires no normality assumption

These findings were found from sources online and research providing that the data could not be normally distributed across. 
Here is an article I found useful for when and how to use the Mann-Whitney U test: 
https://sheffield.pressbooks.pub/help4jasp/chapter/independent-t-test/
A p-value < 0.05 is used as the significance threshold.
