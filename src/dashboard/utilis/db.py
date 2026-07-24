from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st

DB_PATH = Path("db/nifty100.db")


@st.cache_data(ttl=600)
def run_query(query, params=None):
    
    conn = sqlite3.connect(DB_PATH)
    
    df = pd.read_sql_query(
        query,
        conn,
        params=params
    )
    
    conn.close()
    
    return df


@st.cache_data(ttl=600)
def get_companies():
    
    return run_query("""
        SELECT DISTINCT company_id
        FROM financial_ratios
        ORDER BY compny_id
    """)
    

@st.cache_data(ttl=600)
def get_ratios(company_id):
    
    return run_query(
        """
        SELECT *
        FROM financial_ratios
        WHERE company_id=?
        ORDER BY year
        """,
        (company_id,)
    )
    
    
@st.cache_data(ttl=600)
def get_peer_percentiles():
    
    return run_query("""
        SELECT *
        FROM peer_percentiles
    """)
    
    
@st.cache_data(ttl=600)
def get_sectors():
    
    return run_query("""
        SELECT *
        FROM sectors
    """)