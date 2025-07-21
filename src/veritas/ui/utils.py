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

    Using @st.cache_resource ensures that the SessionManager and its underlying
    data repository are created only once per session, which is highly efficient.
    The SessionManager instance is then available to all pages for the duration
    of the user's interaction with the app.
    
    Returns:
        SessionManager: The singleton instance for the current user session.
    """
    logger.info("CORE: Initializing SessionManager for the first time this session.")
    try:
        # Import moved inside to avoid runtime circular dependency
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
    2. Checks if the user is logged in. If not, it stops execution and prompts login.
    3. Checks if the logged-in user has the correct role to view the specific page.
    4. If all checks pass, it returns the session-wide business logic controller.

    Args:
        page_title (str): The title of the page.
        page_icon (str): The emoji icon for the page.

    Returns:
        SessionManager: The active business logic controller for the session.
    """
    # 1. Set the page configuration. This must be the first `st` command.
    st.set_page_config(page_title=f"VERITAS | {page_title}", page_icon=page_icon, layout="wide")
    
    # 2. Check if the user is logged in. If not, redirect to login page and stop.
    if not st.session_state.get('is_authenticated'):
        st.warning("🔒 You must be logged in to access this page.")
        st.page_link("app.py", label="Go to Login Page", icon="🏠")
        st.stop()
        
    # 3. CRITICAL FIX: If logged in, check if their role is authorized for THIS page.
    # This call handles the logic that previously caused the AttributeError.
    auth.check_page_authorization()
    
    # 4. If all checks pass, retrieve the session manager and return it for the page to use.
    manager = get_session_manager()
    
    # Add a logout button to the sidebar of every authenticated page.
    with st.sidebar:
        st.markdown("---")
        st.write(f"Logged in as: **{st.session_state.get('username')}**")
        st.write(f"Role: **{st.session_state.get('user_role')}**")
        if st.button("Log Out", use_container_width=True):
            auth.perform_logout()
            
    return manager

@st.cache_data(ttl=600)
def get_cached_data(data_key: str) -> pd.DataFrame:
    """
    A generic, cached function to fetch data tables from the repository.

    Using @st.cache_data is ideal for fetching data that doesn't change frequently.
    It prevents re-running the data-fetching logic on every page interaction,
    significantly speeding up the app. The 'ttl' (time-to-live) argument
    ensures the cache is invalidated after 10 minutes (600 seconds), allowing
    for periodic data refreshes.

    Args:
        data_key (str): The key of the dataset to retrieve (e.g., 'hplc').

    Returns:
        pd.DataFrame: A cached copy of the requested DataFrame.
    """
    logger.info(f"DATA_CACHE: Fetching '{data_key}' data from source (cache miss or TTL expired)...")
    try:
        manager = get_session_manager()
        data = manager.get_data(data_key)
        # Return a copy to ensure the cached object is not mutated.
        return data.copy()
    except Exception as e:
        logger.error(f"Failed to load required data ('{data_key}'): {e}", exc_info=True)
        st.error(f"Failed to load required data ('{data_key}'). The application may not function correctly.")
        return pd.DataFrame()
