import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import streamlit as st


DATA_URL = "https://raw.githubusercontent.com/opensource-observer/oss-funding/main/funding_data.csv"
SLUG_COL = 'oso_slug'
NAME_COL = 'project_name'
FUND_COL = 'funding_usd'
CAT_COLS = [
    'funder_name',
    'funder_round_name',
    'project_name_mapping'
]
VAL_COLS = [
    'funding_usd', 
    'funding_usd_log',
    'funding_event_count'
]

@st.cache_data
def load_data(url=DATA_URL):    
    
    # Read the data from the URL
    df = pd.read_csv(url, index_col=0)

    # Is OSS project
    df['is_oss'] = df[SLUG_COL].apply(lambda x: x is not np.nan)

    # Map project names to slug
    df[SLUG_COL] = df[SLUG_COL].apply(lambda x: min(x.split(','), key=len) if isinstance(x, str) else x)    
    df[SLUG_COL] = df[SLUG_COL].fillna(df[NAME_COL].apply(lambda x: x.replace(",","").replace(" ","_").lower()))
    df['project_name_mapping'] = df[SLUG_COL].map(df.groupby(SLUG_COL)[NAME_COL].apply(lambda x: x.value_counts().idxmax()))
    df['project_name_mapping'] = df['project_name_mapping'].apply(lambda x: x[:20] + '...' if len(x) > 20 else x)    
    df['project_name_mapping'] = df.apply(lambda x: f"{x['project_name_mapping']} (project)" if x['funder_name'] in x['project_name_mapping'] else x['project_name_mapping'], axis=1)
    df['project_name_mapping'].replace("Synpress", "Synthetix / Synpress", inplace=True)

    # Add variants of funding columns
    df['funding_usd_log'] = np.log10(df[FUND_COL])
    df['funding_event_count'] = 1
    df['funding_event_sum'] = df.groupby('project_name_mapping')['funding_event_count'].transform('sum')
    df['funding_usd_sum'] = df.groupby('project_name_mapping')['funding_usd'].transform('sum')

    df['funding_year'] = pd.to_datetime(df['funding_date']).dt.year

    return df


def make_sankey_graph(
    df, 
    cat_cols=CAT_COLS, 
    value_col=FUND_COL,
    main_color="purple",
    med_color="teal",
    light_color="green",
    width=1000, 
    height=1200, 
    size=12,
    decimals=True,
    hide_label_cols=[]):

    # build the title info
    total = df[value_col].sum()
    max_nodes = max(df[cat_cols].nunique())
    line_width = min(.5, (height / max_nodes / 50))

    # make the Sankey
    labelList = []
    nodeLabelList = []
    colorNumList = []
    for catCol in cat_cols:
        labelListTemp = list(set(df[catCol].values))        
        colorNumList.append(len(labelListTemp))
        labelList = labelList + labelListTemp
        if catCol in hide_label_cols:
            nodeLabelList = nodeLabelList + [""] * len(labelListTemp)
        else:
            nodeLabelList = nodeLabelList + labelListTemp

    # remove duplicates from labelList
    labelList = list(dict.fromkeys(labelList))

    # define colors based on number of categories
    colorPalette = [main_color, med_color, light_color]
    colorList = []
    for idx, colorNum in enumerate(colorNumList):
        colorList = colorList + [colorPalette[idx]]*colorNum

    # transform df into a source-target pair
    for i in range(len(cat_cols)-1):
        if i==0:
            sourceTargetDf = df[[cat_cols[i], cat_cols[i+1], value_col]]
            sourceTargetDf.columns = ['source','target','value']
        else:
            tempDf = df[[cat_cols[i],cat_cols[i+1],value_col]]
            tempDf.columns = ['source','target','value']
            sourceTargetDf = pd.concat([sourceTargetDf,tempDf])
        sourceTargetDf = sourceTargetDf.groupby(['source','target']).agg({'value':'sum'}).reset_index()

    # add index for source-target pair
    sourceTargetDf['sourceID'] = sourceTargetDf['source'].apply(lambda x: labelList.index(x))
    sourceTargetDf['targetID'] = sourceTargetDf['target'].apply(lambda x: labelList.index(x))

    linkLabels = []
    for c in cat_cols:
        linkLabels += [c] * df[c].nunique()

    # creating the sankey diagram
    pad = 15
    node_thickness = 10
    data = dict(
        type='sankey',
        orientation='h',
        domain=dict(x=[0,1], y=[0,1]),
        arrangement='freeform',
        node=dict(
          thickness=node_thickness,
          line=dict(color=main_color, width=line_width), 
          label=nodeLabelList,
          color=colorList,
          customdata=linkLabels,
          hovertemplate="<br>".join([
                "<b>%{value:,.1f}</b>" if decimals else "<b>%{value:,.0f}</b>",
                "%{customdata}: %{label}",
                "<extra></extra>"
            ])
        ),
        link=dict(
          source=sourceTargetDf['sourceID'],
          target=sourceTargetDf['targetID'],
          value=sourceTargetDf['value'],
          hovertemplate="<br>".join([
                "<b>%{value:,.1f}</b>" if decimals else "<b>%{value:,.0f}</b>",
                "%{source.customdata}: %{source.label}",
                "%{target.customdata}: %{target.label}",
                "<extra></extra>"
            ])
        )
      )

    xpad = ((node_thickness+pad)/2)/width
    xpos = np.linspace(xpad, 1-xpad, len(cat_cols))

    layout = dict(
        font=dict(color=main_color, size=size), 
        autosize=True,
        height=height
    )
    fig = dict(data=[data], layout=layout)
    return fig


st.title('Ethereum Ecosystem Grant Funding')

data_load_state = st.text('Loading data...')
data = load_data()
data_load_state.text('Loading data...done!')

total_funding = data['funding_usd'].sum()
st.subheader(f'Total grant funding: ${total_funding:,.0f}')
st.bar_chart(data.groupby('funding_year')['funding_usd'].sum().sort_values(ascending=False))

tab1, tab2 = st.tabs(["Ecosytem View", "Project View"])


with tab1:
    ecosystems_to_filter = st.multiselect('Select ecosystem(s)', data['funder_name'].unique(), data['funder_name'].unique())
    usd_to_filter = st.slider('Minimum project funding threshold (USD)', 1, 500_000, 100_000)
    round_to_filter = st.slider('Minimum project grant rounds threshold', 1, 10, 2)
    log_scale = st.radio('Log scale', ['Yes', 'No'])

    if log_scale == 'Yes':
        fund_col = 'funding_usd_log'
    else:
        fund_col = 'funding_usd'

    filtered_data = data[
        (data['funder_name'].isin(ecosystems_to_filter)) &
        (data['funding_usd_sum'] >= usd_to_filter) &
        (data['funding_event_sum'] >= round_to_filter)
    ]

    fig = make_sankey_graph(df=filtered_data, value_col=fund_col)
    st.plotly_chart(fig)

with tab2:
    project_name = st.text_input('Project name or keyword', 'Protocol Guild')
    filtered_data = data[data['project_name_mapping'].str.contains(project_name, case=False)]

    total_funding = filtered_data['funding_usd'].sum()
    total_rounds = filtered_data['funding_event_count'].sum()
    st.subheader(f'Total grant funding: ${total_funding:,.0f}')
    fig = make_sankey_graph(
        df=filtered_data,
        height=800, 
        cat_cols=['funder_name', 'funder_round_name', 'project_name']
    )
    st.plotly_chart(fig)