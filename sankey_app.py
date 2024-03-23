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
    #df['project_name_mapping'] = df[SLUG_COL].map(df.groupby(SLUG_COL)[NAME_COL].apply(lambda x: x.value_counts().idxmax()))
    project_names = pd.read_csv('project_names.csv', index_col=0)['project_name'].to_dict()
    df['project_name_mapping'] = df.apply(lambda x: project_names.get(x[SLUG_COL], x[NAME_COL]), axis=1)
    
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
    size=10,
    height=1000,
    decimals=False,
    hide_label_cols=[]):

    # populate the Sankey data
    labelList = []
    nodeLabelList = []
    for catCol in cat_cols:
        labelListTemp = list(set(df[catCol].values))        
        labelList = labelList + labelListTemp
        if catCol in hide_label_cols:
            nodeLabelList = nodeLabelList + [""] * len(labelListTemp)
        else:
            nodeLabelList = nodeLabelList + labelListTemp

    # remove duplicates from labelList
    labelList = list(dict.fromkeys(labelList))

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

    # create the Sankey diagram
    pad = 5
    node_thickness = 20
    line_width = .25
    data = dict(
        type='sankey',
        orientation='h',
        domain=dict(x=[0,1], y=[0,1]),
        arrangement='freeform',
        node=dict(
          thickness=node_thickness,
          line=dict(width=line_width), 
          label=nodeLabelList,
          customdata=linkLabels,
          hovertemplate="<br>".join([
                "<b>%{label}</b>",
                "$%{value:,.2f}" if decimals else "$%{value:,.0f}"
                "<extra></extra>"
            ])
        ),
        link=dict(
          source=sourceTargetDf['sourceID'],
          target=sourceTargetDf['targetID'],
          value=sourceTargetDf['value'],
          hovertemplate="<br>".join([
                "<b>%{source.label} -> %{target.label}</b>",
                "$%{value:,.2f}" if decimals else "$%{value:,.0f}",
                "<extra></extra>"
            ])
        )
    )
    layout = dict(
        font=dict(size=size), 
        height=height,
        autosize=True,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    fig = dict(data=[data], layout=layout)
    return fig


st.set_page_config(layout="wide")
st.title('Ethereum Ecosystem Grant Funding')

data_load_state = st.text('Loading data...')
data = load_data()
data_load_state.text(f'Loaded {data.shape[0]:,} grant funding records.')

total_funding = data['funding_usd'].sum()
st.subheader(f'Total grant funding: ${total_funding:,.0f}')
st.bar_chart(data.groupby('funding_year')['funding_usd'].sum().sort_values(ascending=False), height=300, color='#aaa')

tab1, tab2 = st.tabs(["Ecosytem View", "Project View"])

with tab1:
    ecosystems_to_filter = st.multiselect('Select ecosystem(s)', data['funder_name'].unique(), data['funder_name'].unique())
    usd_to_filter = st.slider('Minimum project funding threshold (USD)', 1, 500_000, 100_000)
    round_to_filter = st.slider('Minimum project grant rounds threshold', 1, 10, 2)
    log_scale = st.radio('Log scale', ['No', 'Yes'])

    if log_scale == 'Yes':
        fund_col = 'funding_usd_log'
    else:
        fund_col = 'funding_usd'

    st.subheader('Ecosystem funding snapshot')

    filtered_data = data[
        (data['funder_name'].isin(ecosystems_to_filter)) &
        (data['funding_usd_sum'] >= usd_to_filter) &
        (data['funding_event_sum'] >= round_to_filter)
    ]
    if filtered_data.empty:
        st.write('No data to display. Please adjust the filters.')
        st.stop()
    
    fig = make_sankey_graph(df=filtered_data, value_col=fund_col, height=1200)
    
    annotation = "<br>".join([
        f"<b>Total grant funding:</b> ${filtered_data['funding_usd'].sum():,.0f}",
        f"<b>Projects:</b> {filtered_data['project_name_mapping'].nunique():,.0f}",
        f"<b>Grant disbursements:</b> {filtered_data['funding_event_count'].sum():,.0f}"
    ])
    fig['layout'].update({
        'annotations': [
            dict(x=0, y=1,
                showarrow=False,
                text=annotation,
                font=dict(size=14, color='black'),
                align='left')
        ]
    })

    st.plotly_chart(fig, use_container_width=True)

with tab2:
    project_name = st.text_input('Project name or keyword', 'Protocol Guild')
    filtered_data = data[data['project_name_mapping'].str.contains(project_name, case=False)]

    total_funding = filtered_data['funding_usd'].sum()
    total_rounds = filtered_data['funding_event_count'].sum()
    st.subheader(f'Total grant funding: ${total_funding:,.0f}')

    if len(filtered_data) > 100:
        st.write('Too much data to display. Please use a more specific keyword.')
        st.stop()
    
    fig = make_sankey_graph(
        df=filtered_data,
        cat_cols=['funder_name', 'funder_round_name', 'project_name'],
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)
