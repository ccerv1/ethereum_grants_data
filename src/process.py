from func_timeout import func_timeout, FunctionTimedOut
import numpy as np
import pandas as pd

DATA_URL = 'https://raw.githubusercontent.com/opensource-observer/oss-funding/main/funding_data.csv'
LOCAL_PATH = 'data/funding_data.csv'

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

def fetch_data(timeout):

    def read_csv(path):
        return pd.read_csv(path, index_col=0)

    try:
        return func_timeout(timeout, read_csv, args=(DATA_URL,))
    except FunctionTimedOut:
        return read_csv(LOCAL_PATH)
    except Exception as e:
        print(f"An error occurred: {e}.")
        return None
    

def process_dataframe(timeout=3):

    df = fetch_data(timeout)

    # Map project names to slug
    df[SLUG_COL] = df[SLUG_COL].apply(lambda x: min(x.split(','), key=len) if isinstance(x, str) else x)    
    df[SLUG_COL] = df[SLUG_COL].fillna(df[NAME_COL].apply(lambda x: x.replace(",","").replace(" ","_").lower()))
    
    project_names = pd.read_csv('data/project_names.csv', index_col=0)['project_name'].to_dict()
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