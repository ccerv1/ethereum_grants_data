import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import streamlit as st

from src.sankey import make_sankey_graph
from src.process import process_dataframe, CAT_COLS 


@st.cache_data
def load_data():    
    return process_dataframe()


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

    st.subheader('Ecosystem funding snapshot')
    ecosystems_to_filter = st.multiselect('Select ecosystem(s)', data['funder_name'].unique(), data['funder_name'].unique())
    
    col1, col2, col3 = st.columns([3,2,1])
    with col1: 
        usd_to_filter = st.slider('Minimum project funding threshold (USD)', 1, 500_000, 100_000)
    with col2:
        round_to_filter = st.slider('Minimum project grant rounds threshold', 1, 10, 2)
    with col3:
        log_scale = st.radio('Log scale', ['No', 'Yes'])

    if log_scale == 'Yes':
        fund_col = 'funding_usd_log'
    else:
        fund_col = 'funding_usd'
    
    filtered_data = data[
        (data['funder_name'].isin(ecosystems_to_filter)) &
        (data['funding_usd_sum'] >= usd_to_filter) &
        (data['funding_event_sum'] >= round_to_filter)
    ]
    if filtered_data.empty:
        st.write('No data to display. Please adjust the filters.')
        st.stop()
    
    fig = make_sankey_graph(df=filtered_data, cat_cols=CAT_COLS, value_col=fund_col, height=1200)
    
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
                font=dict(size=14),
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
        value_col='funding_usd',
        cat_cols=['funder_name', 'funder_round_name', 'project_name'],
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)
