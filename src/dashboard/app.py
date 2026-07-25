import streamlit as st
import sys
from pathlib import Path

# ---------------------------------------------------------
# Make project root importable
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 Nifty 100 Financial Intelligence Platform")

st.markdown(
    """
    Welcome to the Financial Intelligence Platform.
    
    Use the sidebar to navigate between dashboard pages.
    """
)

st.success("Dashboard initialized successfully.")