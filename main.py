import pandas as pd
import streamlit as st

from src.charts import make_sankey_graph, make_barchart
from src.process import process_dataframe, CAT_COLS 


@st.cache_data
def load_data():    
    return process_dataframe()


st.set_page_config(layout="wide")
data = load_data()
funder_names = sorted(data['funder_name'].unique())


def ecosystem_tab():
    
    ecosystems_to_filter = st.multiselect('Select ecosystem(s)', funder_names, funder_names)
    dff = data[data['funder_name'].isin(ecosystems_to_filter)]
    if dff.empty:
        st.write('No data to display. Please adjust the filters.')
        st.stop()

    ###### Barchart ######

    total_funding = dff['funding_usd'].sum()
    st.subheader(f'💸 Total funding: ${total_funding:,.0f}')
    
    barchart = make_barchart(dff)
    st.plotly_chart(barchart, use_container_width=True)


    ###### Sankey ######

    st.subheader('🔍 Allocation explorer')
    
    # Set additional filters    
    col1, col2, col3, col4, col5, col6 = st.columns([3,1,3,1,1,1])
    with col1: 
        years = sorted(dff['funding_year'].unique())
        years_to_filter = st.multiselect('Select years(s)', years, years[-2:])
    with col3:
        amounts_to_filter = st.slider('Only view grants grants above...', 0, 500_000, 1000, 1000, format='$%d')
    with col5:
        log_scale = st.checkbox('Display log scale', value=False)
    with col6:
        resize_height = st.checkbox('Resize height', value=False)

    # Apply filters
    dfff = dff[(dff['funding_year'].isin(years_to_filter)) & (dff['funding_usd']>=amounts_to_filter)]
    if dfff.empty:
        st.write('No data to display. Please adjust the filters.')
        st.stop()
    fund_col = 'funding_usd_log' if log_scale else 'funding_usd'

    H = 1200
    height = H
    if resize_height:
        height = max(min(2*len(dfff),H*4), H/2)

    annotation = " | ".join([
        f"Funding: ${dfff['funding_usd'].sum():,.0f}",
        f"Rounds: {dfff[CAT_COLS[-2]].nunique():,.0f}",
        f"Projects: {dfff[CAT_COLS[-1]].nunique():,.0f}",
        f"Awards: {len(dfff):,.0f}"
    ])
    st.write(annotation)

    sankey = make_sankey_graph(
        df=dfff,
        cat_cols=CAT_COLS,
        value_col=fund_col,
        height=height
    )
    st.plotly_chart(sankey, use_container_width=True)


def project_tab():

    project_name = st.text_input('Enter a project name or keyword', 'test')
    dff = data[data['project_name_mapping'].str.contains(project_name, case=False)]
    if len(dff) > 100:
        st.write('Too much data to display. Please use a more specific keyword.')
        st.stop()

    
    ###### Barchart ######

    total_funding = dff['funding_usd'].sum()
    st.subheader(f'💸 Total funding: ${total_funding:,.0f}')
    barchart = make_barchart(dff)
    st.plotly_chart(barchart, use_container_width=True)
    
    
    ###### Sankey ######

    st.subheader('🔍 Allocation explorer')

    sankey = make_sankey_graph(
        df=dff,
        value_col='funding_usd',
        cat_cols=['funder_name', 'funder_round_name', 'project_name'],
        height=600
    )
    st.plotly_chart(sankey, use_container_width=True)


###### Main ######

st.title('Grants on Ethereum')
text = " ".join([
        '🏗️',
        f'Dataset currently covers a total of {len(data):,.0f}',
        f'disbursements from {len(funder_names)} grant programs.',
        'Help us add to it [here](https://github.com/opensource-observer/oss-funding)!'
    ])
st.write(text)

tab1, tab2 = st.tabs(["Ecosytem View", "Project View"])
with tab1:
    ecosystem_tab()
with tab2:
    project_tab()