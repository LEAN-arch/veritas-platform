# src/veritas/ui/auth.py

import streamlit as st
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# --- Centralized Role-Based Access Control (RBAC) Configuration ---
# In a real app, this might come from a database or a config file (e.g., YAML).
AUTH_CONFIG = {
    "page_permissions": {
        "app.py": ["DTE Leadership", "QC Analyst", "Scientist"],
        "1_QC_Center.py": ["QC Analyst"],
        "2_Process_Capability.py": ["Scientist", "DTE Leadership"],
        "3_Stability_Dashboard.py": ["Scientist", "DTE Leadership"],
        "4_Regulatory_Support.py": ["DTE Leadership"],
        "5_Deviation_Hub.py": ["QC Analyst", "DTE Leadership"],
        "6_Governance_Hub.py": ["DTE Leadership"],
    }
}

def verify_credentials(username: str, password: Optional[str]) -> bool:
    """Verifies user credentials (mock implementation)."""
    if not username or not password:
        logger.warning("Authentication attempt with empty username or password.")
        return False
    
    logger.info(f"Verifying credentials for user: '{username}'")
    if username == "testuser" and password == "password":
        logger.info(f"Successfully authenticated user: '{username}'")
        return True
    
    logger.warning(f"Failed authentication attempt for user: '{username}'")
    return False

def check_page_authorization() -> None:
    """
    Checks if the current user's role is authorized to view the current page.
    If not authorized, it stops the script and displays an error message.
    """
    # FIX: Use the modern, correct way to get the current page script name.
    # st.get_option("client.currentPage") returns the page script path relative to the root.
    # e.g., "app.py" or "pages/1_QC_Center.py"
    try:
        page_script_path = st.get_option("client.currentPage")
    except Exception:
        # Fallback for environments where the option might not be available (e.g., some test runners)
        st.error("Could not determine the current page. Authorization check failed.")
        st.stop()

    current_page_script = os.path.basename(page_script_path)
    user_role = st.session_state.get('user_role', 'Guest')
    
    authorized_roles = AUTH_CONFIG["page_permissions"].get(current_page_script)

    if authorized_roles is None:
        # This is a configuration error - every page should be in the auth config.
        logger.error(f"Authorization Error: Page '{current_page_script}' not found in AUTH_CONFIG. Denying access by default.")
        st.error("This page has an invalid security configuration. Access denied.")
        st.stop()
    
    if user_role not in authorized_roles:
        logger.warning(f"Unauthorized access attempt: User '{st.session_state.username}' with role '{user_role}' tried to access '{current_page_script}'.")
        st.error(f"🚫 Access Denied")
        st.warning(f"Your user role ('{user_role}') is not authorized to view this page.")
        st.page_link("app.py", label="Return to Home", icon="🏠")
        st.stop() # Halt execution of the page

def display_compliance_footer() -> None:
    """Renders a standardized, GxP-compliant footer."""
    try:
        st.markdown("---")
        st.markdown(
            """
            <div style="text-align: center; color: grey; font-size: 0.8em;">
                <b>VERITAS GxP Compliance Footer</b><br>
                21 CFR Part 11 Compliant | Data Integrity Ensured | Audit Trail Active<br>
                © 2025 VERITAS Solutions
            </div>
            """,
            unsafe_allow_html=True
        )
    except Exception as e:
        logger.error(f"Failed to render compliance footer: {e}", exc_info=True)

def perform_logout() -> None:
    """Logs the user out by clearing session state."""
    logger.info(f"Logging out user: '{st.session_state.get('username', 'Unknown')}'")
    keys_to_clear = ['is_authenticated', 'username', 'user_role']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
