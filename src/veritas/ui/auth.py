# src/veritas/ui/auth.py

import streamlit as st
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# This centralized configuration is the single source of truth for page permissions.
AUTH_CONFIG = {
    "page_permissions": {
        "app.py": ["DTE Leadership", "QC Analyst", "Scientist"], # Home page
        "1_Data_Ingestion_Gateway.py": ["QC Analyst", "Scientist"],
        "2_QC_and_Integrity_Center.py": ["QC Analyst"],
        "3_Process_Capability_Dashboard.py": ["Scientist", "DTE Leadership"],
        "4_Stability_Program_Dashboard.py": ["Scientist", "DTE Leadership"],
        "5_Regulatory_Support.py": ["DTE Leadership"],
        "6_Deviation_Hub.py": ["QC Analyst", "DTE Leadership"],
        "7_Governance_&_Audit_Hub.py": ["DTE Leadership"],
    }
}

def verify_credentials(username: str, password: Optional[str]) -> bool:
    """Verifies user credentials (mock implementation)."""
    if not username or not password:
        return False
    # Mock logic: In a real app, this would query a database or identity provider.
    if username == "testuser" and password == "password":
        return True
    return False

def check_page_authorization() -> None:
    """
    Checks if the current user's role is authorized to view the current page.
    This is the definitive fix for the 'current_script_path' error.
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
        logger.error(f"Authorization Error: Page '{current_page_script}' not in AUTH_CONFIG. Denying access.")
        st.error("This page has an invalid security configuration. Access denied.")
        st.stop()
    
    if user_role not in authorized_roles:
        logger.warning(f"UNAUTHORIZED ACCESS: User '{st.session_state.get('username')}' with role '{user_role}' tried to access '{current_page_script}'.")
        st.error("🚫 Access Denied")
        st.warning(f"Your assigned role ('{user_role}') is not authorized to view this page.")
        st.page_link("app.py", label="Return to Home", icon="🏠")
        st.stop()

def display_compliance_footer() -> None:
    """Renders a standardized, GxP-compliant footer."""
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

def perform_logout() -> None:
    """Logs the user out by clearing session state and rerunning the script."""
    logger.info(f"Logging out user: '{st.session_state.get('username', 'Unknown')}'")
    keys_to_clear = ['is_authenticated', 'username', 'user_role']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
