# src/veritas/ui/auth.py

import streamlit as st
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# This centralized configuration is the single source of truth for page permissions.
# NOTE: 'DTE Leadership' (the role for 'testuser') has been granted access to ALL pages.
AUTH_CONFIG = {
    "page_permissions": {
        "app.py": ["DTE Leadership", "QC Analyst", "Scientist", "Guest"],
        "1_Data_Ingestion_Gateway.py": ["DTE Leadership", "QC Analyst", "Scientist"],
        "2_QC_and_Integrity_Center.py": ["DTE Leadership", "QC Analyst"],
        "3_Process_Capability_Dashboard.py": ["DTE Leadership", "Scientist"],
        "4_Stability_Program_Dashboard.py": ["DTE Leadership", "Scientist"],
        "5_Regulatory_Support.py": ["DTE Leadership"],
        "6_Deviation_Hub.py": ["DTE Leadership", "QC Analyst"],
        "7_Governance_and_Audit_Hub.py": ["DTE Leadership"],
    }
}

def verify_credentials(username: str, password: Optional[str]) -> bool:
    """Verifies user credentials (mock implementation)."""
    if not username or not password:
        return False
    if username == "testuser" and password == "password":
        logger.info(f"Successful login attempt for user: '{username}'")
        return True
    logger.warning(f"Failed login attempt for user: '{username}'")
    return False

def check_page_authorization() -> None:
    """
    Checks if the current user's role is authorized to view the current page.
    This function contains the definitive fix for the 'current_script_path' AttributeError.
    """
    #
    # >>>>> DEFINITIVE FIX IS HERE <<<<<
    # The failing 'st.current_script_path' is replaced with 'st.get_option'.
    #
    try:
        page_script_path = st.get_option("client.currentPage")
    except Exception as e:
        logger.error(f"Could not determine current page via st.get_option: {e}", exc_info=True)
        st.error("Fatal Error: Could not determine the current page for authorization check.")
        st.stop()

    current_page_script = os.path.basename(page_script_path)
    user_role = st.session_state.get('user_role', 'Guest')
    
    authorized_roles = AUTH_CONFIG["page_permissions"].get(current_page_script)

    if authorized_roles is None:
        logger.critical(f"Authorization Error: Page '{current_page_script}' not found in AUTH_CONFIG. Denying access.")
        st.error(f"This page has an invalid security configuration. Access denied.")
        st.stop()
    
    if user_role not in authorized_roles:
        logger.warning(f"UNAUTHORIZED ACCESS: User '{st.session_state.get('username')}' with role '{user_role}' tried to access '{current_page_script}'.")
        st.error("🚫 Access Denied")
        st.warning(f"Your assigned role ('{user_role}') is not authorized to view this page.")
        st.page_link("app.py", label="Return to Mission Control", icon="🏠")
        st.stop()
    
    logger.info(f"AUTHORIZED ACCESS: User '{st.session_state.get('username')}' (Role: '{user_role}') granted access to '{current_page_script}'.")

def perform_logout() -> None:
    """Logs the user out by clearing session state and rerunning."""
    username = st.session_state.get('username', 'Unknown')
    logger.info(f"Logging out user: '{username}'")
    keys_to_clear = ['is_authenticated', 'username', 'user_role']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
