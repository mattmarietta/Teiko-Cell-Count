import sqlite3
import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, dash_table, Input, Output
import dash_bootstrap_components as dbc

from analysis import (
    get_frequency_table,
    get_responder_data,
    statistics_analysis,
    make_boxplot,
    get_samples_per_project,
    responders_non_responders,
    males_females,
    avg_number_B_cells,
    DB_PATH,
)


freq_df     = get_frequency_table()
resp_df     = get_responder_data()
stats_df    = statistics_analysis(resp_df)
boxplot     = make_boxplot(resp_df)
proj_df     = get_samples_per_project()
resp_grp_df = responders_non_responders()
gender_df   = males_females()
avg_bcell   = avg_number_B_cells()

# Load raw samples for the explorer tab
conn   = sqlite3.connect(DB_PATH)
raw_df = pd.read_sql_query("SELECT * FROM samples", conn)
conn.close()


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])


app.layout = dbc.Container([

    html.H2("Immune Cell Population Analysis", className="mt-4 mb-0"),
    html.P("Clinical Trial Dashboard", className="text-muted mb-4"),

    dbc.Tabs([

        # Tab 1: Frequency Table 
        dbc.Tab(label="Data Overview", children=[
            html.P("Relative frequency of each cell population per sample.", className="mt-3 text-muted"),

            dbc.Input(id="search", placeholder="Search sample or population...", debounce=True, className="mb-3 w-25"),
            html.Small(id="row-count", className="text-muted d-block mb-2"),

            dash_table.DataTable(
                id="freq-table",
                columns=[{"name": c, "id": c} for c in freq_df.columns],
                data=freq_df.to_dict("records"),
                page_size=15,
                sort_action="native",
                style_cell={"fontSize": 13, "padding": "6px 12px"},
                style_header={"fontWeight": "bold", "backgroundColor": "#f4f6f8"},
                style_table={"overflowX": "auto"},
            )
        ]),

        # Tab 2: Responder Analysis
        dbc.Tab(label="Responder Analysis", children=[
            html.P("Melanoma patients on miraclib (PBMC only) — responders vs non-responders.", className="mt-3 text-muted"),

            dcc.Graph(figure=boxplot),

            html.Hr(),
            html.H6("Mann-Whitney U Test Results"),
            html.P("p < 0.05 = statistically significant difference between groups.", className="text-muted small"),

            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in stats_df.columns],
                data=stats_df.to_dict("records"),
                style_cell={"fontSize": 13, "padding": "6px 12px"},
                style_header={"fontWeight": "bold", "backgroundColor": "#f4f6f8"},
                style_data_conditional=[{
                    "if": {"filter_query": '{significant} = "YES"'},
                    "backgroundColor": "#d4edda",
                    "fontWeight": "bold"
                }]
            )
        ]),

        # Subset Analysis
        dbc.Tab(label="Subset Analysis", children=[
            html.P("Baseline melanoma PBMC samples — miraclib, time = 0.", className="mt-3 text-muted"),

            # Key numbers
            dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([html.P("Total Samples", className="text-muted small mb-1"), html.H4("656")])), md=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.P("Projects",       className="text-muted small mb-1"), html.H4("2")])),   md=3),
                dbc.Col(dbc.Card(dbc.CardBody([html.P("Avg B Cells (Male Responders)", className="text-muted small mb-1"), html.H4(str(avg_bcell))])), md=3),
            ], className="mb-4 g-3"),

            # Bar charts
            dbc.Row([
                dbc.Col(dcc.Graph(figure=px.bar(proj_df,     x="project",  y="sample_count",  title="Samples per Project",         text="sample_count",  template="plotly_white").update_traces(textposition="outside")), md=4),
                dbc.Col(dcc.Graph(figure=px.bar(resp_grp_df, x="response", y="subject_count", title="Responders vs Non-Responders", text="subject_count", template="plotly_white", color="response", color_discrete_map={"yes": "#198754", "no": "#dc3545"}).update_traces(textposition="outside")), md=4),
                dbc.Col(dcc.Graph(figure=px.bar(gender_df,   x="sex",      y="subject_count", title="Males vs Females",             text="subject_count", template="plotly_white", color="sex", color_discrete_map={"M": "#0dcaf0", "F": "#fd7e14"}).update_traces(textposition="outside")), md=4),
            ]),
        ]),

        # Data Explorer 
        dbc.Tab(label="Data Explorer", children=[
            html.P("Filter the full sample metadata by any field.", className="mt-3 text-muted"),

            dbc.Row([
                dbc.Col([html.Label("Condition"),  dcc.Dropdown(id="f-condition",  options=[{"label": v, "value": v} for v in sorted(raw_df["condition"].dropna().unique())],              multi=True, placeholder="All")], md=2),
                dbc.Col([html.Label("Treatment"),  dcc.Dropdown(id="f-treatment",  options=[{"label": v, "value": v} for v in sorted(raw_df["treatment"].dropna().unique())],              multi=True, placeholder="All")], md=2),
                dbc.Col([html.Label("Response"),   dcc.Dropdown(id="f-response",   options=[{"label": v, "value": v} for v in ["yes", "no"]],                                             multi=True, placeholder="All")], md=2),
                dbc.Col([html.Label("Sex"),        dcc.Dropdown(id="f-sex",        options=[{"label": v, "value": v} for v in ["M", "F"]],                                                multi=True, placeholder="All")], md=2),
                dbc.Col([html.Label("Sample Type"),dcc.Dropdown(id="f-sampletype", options=[{"label": v, "value": v} for v in sorted(raw_df["sample_type"].dropna().unique())],            multi=True, placeholder="All")], md=2),
            ], className="mb-3 g-2"),

            html.Small(id="explorer-count", className="text-muted d-block mb-2"),

            dash_table.DataTable(
                id="explorer-table",
                columns=[{"name": c, "id": c} for c in raw_df.columns],
                data=raw_df.to_dict("records"),
                page_size=15,
                sort_action="native",
                style_cell={"fontSize": 12, "padding": "5px 10px"},
                style_header={"fontWeight": "bold", "backgroundColor": "#f4f6f8"},
                style_table={"overflowX": "auto"},
            )
        ]),
    ])

], fluid=True)

# Make callbacks for interactions
@app.callback(
    Output("freq-table", "data"),
    Output("row-count", "children"),
    Input("search", "value"),
)

# Filter the frequency table based on search input for sample or population
def search_freq_table(search):
    df = freq_df
    if search:
        mask = df["sample"].str.contains(search, case=False, na=False) | \
               df["population"].str.contains(search, case=False, na=False)
        df = df[mask]
    return df.to_dict("records"), f"{len(df):,} rows"


# Callback for the data explorer filters
@app.callback(
    Output("explorer-table", "data"),
    Output("explorer-count", "children"),
    Input("f-condition",  "value"),
    Input("f-treatment",  "value"),
    Input("f-response",   "value"),
    Input("f-sex",        "value"),
    Input("f-sampletype", "value"),
)
def filter_explorer(condition, treatment, response, sex, sample_type):
    df = raw_df.copy()
    if condition:   df = df[df["condition"].isin(condition)]
    if treatment:   df = df[df["treatment"].isin(treatment)]
    if response:    df = df[df["response"].isin(response)]
    if sex:         df = df[df["sex"].isin(sex)]
    if sample_type: df = df[df["sample_type"].isin(sample_type)]
    return df.to_dict("records"), f"{len(df):,} of {len(raw_df):,} samples"


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)