# src/veritas/ui/utils.py

import streamlit as st
import pandas as pd
import logging
from typing import TYPE_CHECKING

# Use a type-checking block to prevent circular imports at runtime
if TYPE_CHECKING:
    from ..session_manager import SessionManager

from ..repository import MockDataRepository
from . import auth # Import the corrected auth module

logger = logging.getLogger(__name__)


@st.cache_resource
def get_session_manager() -> 'SessionManager':
    """
    Initializes and returns a singleton SessionManager instance for the user's session.
    """
    logger.info("CORE: Initializing SessionManager for the first time this session.")
    try:
        from ..session_manager import SessionManager
        repo = MockDataRepository(seed=42)
        return SessionManager(repository=repo)
    except Exception as e:
        logger.critical(f"Failed to initialize the session manager: {e}", exc_info=True)
        st.error("A critical error occurred while initializing the user session. The application cannot continue.")
        st.exception(e)
        st.stop()

def initialize_page(page_title: str, page_icon: str) -> 'SessionManager':
    """
    The definitive function to start every page. It MUST be the first call in a page's main() function.

    This function enforces a strict, correct order of operations for every page load:
    1. Sets the page configuration (must be the first Streamlit command).
    2. Checks if the user is logged in.
    3. Checks if the logged-in user has the correct role for the specific page.
    4. If all checks pass, it returns the session-wide business logic controller.
    """
    # Step 1: Set the page configuration. This MUST be the first `st` command.
    st.set_page_config(page_title=f"VERITAS | {page_title}", page_icon=page_icon, layout="wide")
    
    # Step 2: Check if the user is logged in. If not, redirect and stop.
    if not st.session_state.get('is_authenticated'):
        st.warning("🔒 You must be logged in to access this page.")
        st.page_link("app.py", label="Go to Login Page", icon="🏠")
        st.stop()
        
    # Step 3: If logged in, check if their role is authorized for THIS page.
    auth.check_page_authorization()
    
    # Step 4: If all checks pass, retrieve the session manager and return it.
    manager = get_session_manager()
    
    # Add a consistent logout button to the sidebar of every authenticated page.
    with st.sidebar:
        st.markdown("---")
        st.write(f"Logged in as: **{st.session_state.get('username')}**")
        st.write(f"Role: **{st.session_state.get('user_role')}**")
        if st.button("Log Out", use_container_width=True):
            auth.perform_logout()
            
    return manager

@st.cache_data(ttl=600)
def get_cached_data(data_key: str) -> pd.DataFrame:
    """A generic, cached function to fetch data tables from the repository."""
    logger.info(f"DATA_CACHE: Fetching '{data_key}' data (cache miss or TTL expired)...")
    try:
        manager = get_session_manager()
        data = manager.get_data(data_key)
        return data.copy()
    except Exception as e:
        logger.error(f"Failed to load required data ('{data_key}'): {e}", exc_info=True)
        st.error(f"Failed to load required data ('{data_key}'). The application may not function correctly.")
        return pd.DataFrame()
