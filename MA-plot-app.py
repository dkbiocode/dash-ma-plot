#!/usr/bin/env python3
# this is modified from https://dash.plotly.com/interactive-graphing
from dash import Dash, dcc, html, Input, Output, State, callback, dash_table, no_update
import plotly.express as px
import json,sys
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Load environment variables
load_dotenv()

USE_EXAMPLE_DATA = False

# columns to show
columns_to_show_in_table = [ 'WBID', 'geneName', 'stage',
    'log_baseMean', 'log2FoldChange', 'lfcSE',
   # 'stat_enriched','stat_depleted','stat_equal',
    'padj_enriched', 'padj_depleted','padj_equal',
    'outcome_01','outcome_05']

# get Williams et al's data
if USE_EXAMPLE_DATA:
    print("Using example data", file=sys.stderr)
    df = pd.read_csv('example-data/subset.data-for-MA-plot-app.csv.gz', compression="gzip")
else:
    print("Connecting to database...", file=sys.stderr)
    try:
        # Get database credentials from environment
        DB_HOST = os.getenv('DB_HOST')
        DB_PORT = int(os.getenv('DB_PORT', 3306))
        DB_NAME = os.getenv('DB_NAME')
        DB_USER = os.getenv('DB_USER')
        DB_PASSWORD = os.getenv('DB_PASSWORD', '')
        DB_SCHEMA = os.getenv('DB_SCHEMA', 'williams2023')
        DB_TABLE = os.getenv('DB_TABLE', 'log2FoldChangeWide')
        DB_TYPE = os.getenv('DB_TYPE', 'mysql')

        # Create connection string based on database type
        if DB_TYPE.lower() == 'postgresql':
            connection_string = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=disable"
            print(f"Using PostgreSQL connection", file=sys.stderr)
        else:
            connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
            print(f"Using MySQL/MariaDB connection", file=sys.stderr)

        # Create engine and connect
        engine = create_engine(connection_string)

        # Query all stages - will filter by stage in the UI
        query = f"SELECT * FROM {DB_SCHEMA}.{DB_TABLE}"
        print(f"Executing query: {query}", file=sys.stderr)

        df = pd.read_sql(query, engine)
        engine.dispose()

        print(f"Loaded {len(df)} rows from database", file=sys.stderr)

        # Normalize column names (PostgreSQL lowercases, MySQL preserves case)
        column_mapping = {
            'wbid': 'WBID',
            'genename': 'geneName',
            'basemean': 'baseMean',
            'log2foldchange': 'log2FoldChange',
            'lfcse': 'lfcSE'
        }
        df.rename(columns=column_mapping, inplace=True)
        print(f"Normalized column names for compatibility", file=sys.stderr)

    except Exception as e:
        print(f"Database connection failed: {e}", file=sys.stderr)
        print("Falling back to example data...", file=sys.stderr)
        df = pd.read_csv('example-data/subset.data-for-MA-plot-app.csv.gz', compression="gzip")

# add a column
df['log_baseMean'] = np.log(df.baseMean)
df['outcome_01'] = df['outcome_01'].fillna('not significant') 
df['outcome_05'] = df['outcome_05'].fillna('not significant') 
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', 'styles.css']

app = Dash(__name__, external_stylesheets=external_stylesheets)

def generate_table(df, geneNames, max_rows=50):
    if not geneNames:
        return None
    dataframe = df.loc[df['WBID'].isin(geneNames)]
    return dataframe.to_dict("records")


styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}

def create_figure(df_filtered, stage):
    """Create MA plot figure for a given stage"""
    stage_titles = {
        'embryo': 'embryo',
        'L1': 'L1 larvae',
        'L3': 'L3 larvae'
    }
    title = f"MA plot of ELT-2-GFP enriched sorted cells in the {stage_titles.get(stage, stage)}"

    # Define plot order: not significant first (bottom), then enriched, equal, depleted (top)
    plot_order = ['not significant', 'enriched', 'equal', 'depleted']

    # Make a copy to avoid SettingWithCopyWarning
    df_plot = df_filtered.copy()

    # Create categorical with specified order
    df_plot['outcome_01_cat'] = pd.Categorical(
        df_plot['outcome_01'],
        categories=plot_order,
        ordered=True
    )

    # Sort by category to control plot order (bottom to top)
    df_sorted = df_plot.sort_values('outcome_01_cat')

    fig = px.scatter(df_sorted, x="log_baseMean",
                     y="log2FoldChange",
                     color="outcome_01",
                     custom_data=["WBID"],
                     title=title,
                     category_orders={"outcome_01": plot_order})
    fig.update_layout(
        clickmode='event+select',
        uirevision=stage  # Preserve zoom/pan state when clearing selection
    )
    fig.update_traces(
        marker_size=5,
        marker_opacity=1.0,  # Default opacity when nothing selected
        hoverinfo="none",
        hovertemplate=None,
        selected=dict(marker=dict(opacity=1.0)),  # Selected points fully visible
        unselected=dict(marker=dict(opacity=0.4))  # Only dim when selection exists
    )
    return fig

@callback(
    Output("graph-tooltip", "show"),
    Output("graph-tooltip", "bbox"),
    Output("graph-tooltip", "children"),
    Input("basic-interactions", "hoverData"),
)
def display_hover(hoverData):
    if hoverData is None:
        return False, no_update, no_update
    pt = hoverData["points"][0]
    bbox = pt["bbox"]
    wbid = pt["customdata"].pop()

    df_row = df.loc[df['WBID'] == wbid]
    geneName = df_row.iloc[0]['geneName']
    WBID = df_row.iloc[0]['WBID']
    log2FC = df_row.iloc[0]['log2FoldChange']
    outcome_01 = df_row.iloc[0]['outcome_01']
    outcome_05 = df_row.iloc[0]['outcome_05']
    children = [
        html.Div([
            #html.Img(src=img_src, style={"width": "100%"}),
            html.P(f"{geneName} : {WBID}", 
                   style={"color": "darkblue", 
                          "overflow-wrap": "break-word"}),
            html.P(f"outcome at .01: {outcome_01}"),
            html.P(f"outcome at .05: {outcome_05}"),
        ], style={'white-space': 'normal'}) # 'width': '200px', 
    ]

    return True, bbox, children

@callback(
    Output('basic-interactions', 'figure'),
    Input('stage-dropdown', 'value'),
    Input('clear-button', 'n_clicks'),
    State('basic-interactions', 'relayoutData')
)
def update_figure(selected_stage, n_clicks, relayout_data):
    """Update the MA plot when stage selection changes or clear button is clicked"""
    from dash import ctx

    df_filtered = df[df['stage'] == selected_stage]
    fig = create_figure(df_filtered, selected_stage)

    # If clear button was clicked, preserve zoom but force selection reset
    if ctx.triggered_id == 'clear-button' and relayout_data:
        # Restore zoom range if it exists
        if 'xaxis.range[0]' in relayout_data:
            fig.update_xaxes(range=[relayout_data['xaxis.range[0]'], relayout_data['xaxis.range[1]']])
        if 'yaxis.range[0]' in relayout_data:
            fig.update_yaxes(range=[relayout_data['yaxis.range[0]'], relayout_data['yaxis.range[1]']])
        # Change uirevision to clear selection
        fig.update_layout(uirevision=f"{selected_stage}_clear_{n_clicks}")

    return fig

app.layout = html.Div([
    html.H1(children='Interactive MA-plot for RNA-seq from Williams et al. 2023'),
    html.Div([
        html.P(children=["This is a plot of overall gene abundance (log_baseMean) against differential expression (log2FoldChange) of genes in the ",
            html.I(children="C. elegans"),
            " embryonic intestinal cells (cell-sorted). The data are from ",
            html.A(children="Williams et al. 2023",
                    href="https://pubmed.ncbi.nlm.nih.gov/37183501/",
                    target="_new"),
        ]),
        html.Div([
            html.Label("Select developmental stage: ", style={'fontWeight': 'bold', 'marginRight': '10px'}),
            dcc.Dropdown(
                id='stage-dropdown',
                options=[
                    {'label': 'Embryo', 'value': 'embryo'},
                    {'label': 'L1 Larvae', 'value': 'L1'},
                    {'label': 'L3 Larvae', 'value': 'L3'}
                ],
                value='embryo',  # default value
                clearable=False,
                style={'width': '200px', 'display': 'inline-block', 'marginRight': '20px'}
            ),
            html.Button('Clear Selection', id='clear-button', n_clicks=0,
                       style={'display': 'inline-block', 'verticalAlign': 'top'})
        ], style={'marginTop': '10px', 'marginBottom': '20px'}),
                ]),
    dcc.Graph(
        id='basic-interactions',
        clear_on_unhover=True
    ),

    dcc.Tooltip(id="graph-tooltip"),


    html.Div([
        html.H4(children='Selected data'),
        dash_table.DataTable(
            #fixed_columns = {'headers': True, 'data': 3},
            columns=[ { 'name':i, 'id': i} for i in columns_to_show_in_table],
            id='table-data')
    ]),
    html.Hr(),
    html.H4(children='Debug info'),
    html.P(children="Show json object returned dynamically by selecting, clicking, hovering or zooming."),
    html.Div(className='row', children=[
        html.Div([
            dcc.Markdown("""
                **Hover Data**

                Mouse over values in the graph.
            """),
            html.Pre(id='hover-data', style=styles['pre'])
        ], className='three columns'),

        html.Div([
            dcc.Markdown("""
                **Click Data**

                Click on points in the graph.
            """),
            html.Pre(id='click-data', style=styles['pre']),
        ], className='three columns'),

        html.Div([
            dcc.Markdown("""
                **Selection Data**

                Choose the lasso or rectangle tool in the graph's menu
                bar and then select points in the graph.

                Note that if `layout.clickmode = 'event+select'`, selection data also
                accumulates (or un-accumulates) selected data if you hold down the shift
                button while clicking.
            """),
            html.Pre(id='selected-data', style=styles['pre']),
        ], className='three columns'),

        html.Div([
            dcc.Markdown("""
                **Zoom and Relayout Data**

                Click and drag on the graph to zoom or click on the zoom
                buttons in the graph's menu bar.
                Clicking on legend items will also fire
                this event.
            """),
            html.Pre(id='relayout-data', style=styles['pre']),
        ], className='three columns')
    ])
])

@callback(
    Output('hover-data', 'children'),
    Input('basic-interactions', 'hoverData'))
def display_hover_data(hoverData):
    return json.dumps(hoverData, indent=2)


@callback(
    Output('click-data', 'children'),
    Input('basic-interactions', 'clickData'))
def display_click_data(clickData):
    return json.dumps(clickData, indent=2)


@callback(
    Output('selected-data', 'children'),
    Input('basic-interactions', 'selectedData'))
def display_selected_data(selectedData):
    return json.dumps(selectedData, indent=2)

@callback(
    Output('table-data', 'data'),
    Input('basic-interactions', 'selectedData'),
    Input('stage-dropdown', 'value'))
def showtable_selected_data(selectedData, selected_stage):
    geneNames = None
    #print(selectedData, file=sys.stderr)
    if selectedData:
        geneNames = [record['customdata'].pop() for record in selectedData['points']]

    # Filter dataframe by selected stage
    df_filtered = df[df['stage'] == selected_stage]
    return generate_table(df_filtered, geneNames, max_rows=50)

""" @callback(
    Output('relayout-data', 'children'),
    Input('basic-interactions', 'reLayoutData'))
def display_relayout_data(relayoutData):
    return json.dumps(relayoutData, indent=2)

 """
if __name__ == '__main__':
    app.run(debug=True)
