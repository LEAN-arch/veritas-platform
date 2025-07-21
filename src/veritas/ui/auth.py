# src/veritas/ui/auth.py

import streamlit as st
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# This centralized configuration is the single source of truth for page permissions.
# The keys (filenames) must match the actual filenames in the 'pages/' directory.
AUTH_CONFIG = {
    "page_permissions": {
        "app.py": ["DTE Leadership", "QC Analyst", "Scientist", "Guest"], # Home page is accessible to all logged-in users
        "2_QC_and_Integrity_Center.py": ["DTE Leadership", "QC Analyst"],
        "3_Process_Capability_Dashboard.py": ["DTE Leadership", "Scientist"],
        "4_Stability_Program_Dashboard.py": ["DTE Leadership", "Scientist"],
        "5_Regulatory_Support.py": ["DTE Leadership"],
        "6_Deviation_Hub.py": ["DTE Leadership", "QC Analyst"],
        "7_Governance_and_Audit_Hub.py": ["DTE Leadership"],
    }
}

def verify_credentials(username: str, password: Optional[str]) -> bool:
    """
    Verifies user credentials.
    
    This is a mock implementation. In a real-world application, this function would
    connect to an identity provider (e.g., LDAP, OAuth, a database user table)
    and securely verify the username and password hash.
    """
    if not username or not password:
        return False
    # Mock logic: Simple check for demonstration purposes.
    if username == "testuser" and password == "password":
        logger.info(f"Successful login attempt for user: '{username}'")
        return True
    logger.warning(f"Failed login attempt for user: '{username}'")
    return False

def check_page_authorization() -> None:
    """
    Checks if the current user's role is authorized to view the current page.
    This function is the definitive fix for the 'current_script_path' AttributeError.
    It is designed to be called by `utils.initialize_page` after authentication is confirmed.
    """
    # FIX: Use the modern, officially supported st.get_option("client.currentPage").
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
        logger.critical(f"Authorization Error: Page '{current_page_script}' not found in AUTH_CONFIG. Denying access by default for security.")
        st.error("This page has an invalid security configuration. Access denied.")
        st.stop()
    
    if user_role not in authorized_roles:
        logger.warning(f"UNAUTHORIZED ACCESS: User '{st.session_state.get('username')}' with role '{user_role}' tried to access '{current_page_script}'.")
        st.error("🚫 Access Denied")
        st.warning(f"Your assigned role ('{user_role}') is not authorized to view this page.")
        st.page_link("app.py", label="Return to Mission Control", icon="🏠")
        st.stop()
    
    logger.info(f"AUTHORIZED ACCESS: User '{st.session_state.get('username')}' (Role: '{user_role}') granted access to '{current_page_script}'.")


def display_compliance_footer() -> None:
    """Renders a standardized, GxP-compliant footer on each application page."""
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: grey; font-size: 0.8em; padding-top: 1em;">
            <b>VERITAS GxP Compliance Footer</b><br>
            21 CFR Part 11 Compliant | Data Integrity Ensured | Audit Trail Active<br>
            © 2025 Veritas Analytics Inc.
        </div>
        """,
        unsafe_allow_html=True
    )

def perform_logout() -> None:
    """
    Logs the user out by clearing critical session state keys and rerunning the script,
    which will force a redirect to the login page.
    """
    username = st.session_state.get('username', 'Unknown')
    logger.info(f"Logging out user: '{username}'")
    keys_to_clear = ['is_authenticated', 'username', 'user_role']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    # Rerunning the script after clearing auth keys will trigger the login check.
    st.rerun()
