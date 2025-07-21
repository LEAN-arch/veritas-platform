# src/veritas/ui/utils.py

import streamlit as st
import pandas as pd
import logging
from ..repository import MockDataRepository
from ..session_manager import SessionManager
from . import auth # Import the auth module

logger = logging.getLogger(__name__)

@st.cache_resource
def get_session_manager() -> SessionManager:
    """Initializes and returns a singleton SessionManager instance using caching."""
    logger.info("CORE: Initializing SessionManager for the first time this session.")
    try:
        repo = MockDataRepository(seed=42)
        return SessionManager(repository=repo)
    except Exception as e:
        st.error("A critical error occurred while initializing the user session.")
        st.exception(e)
        st.stop()

def initialize_page(page_title: str, page_icon: str):
    """
    A single function to be called at the top of every page's main() function.
    It now handles page config, authentication status, AND role-based authorization.
    """
    st.set_page_config(page_title=f"VERITAS | {page_title}", page_icon=page_icon, layout="wide")
    
    # 1. Check if the user is logged in at all.
    if not st.session_state.get('is_authenticated'):
        st.warning("🔒 You are not logged in. Please go to the Home page to log in.")
        st.page_link("app.py", label="Go to Login", icon="🏠")
        st.stop()
        
    # 2. If logged in, check if their role is authorized for THIS specific page.
    #    This is the new, correct place for this call.
    auth.check_page_authorization()
    
    # 3. If authorization passes, return the session manager.
    return get_session_manager()

@st.cache_data(ttl=600)
def get_cached_data(data_key: str) -> pd.DataFrame:
    """A generic, cached function to fetch data tables from the repository."""
    logger.info(f"DATA: Fetching '{data_key}' data from source...")
    try:
        manager = get_session_manager()
        data = manager.get_data(data_key)
        if not isinstance(data, pd.DataFrame):
            raise ValueError(f"Data for key '{data_key}' is not a DataFrame.")
        return data.copy()
    except Exception as e:
        st.error(f"Failed to load required data ('{data_key}').")
        st.exception(e)
        return pd.DataFrame()
