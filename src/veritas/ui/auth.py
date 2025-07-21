# src/veritas/ui/auth.py
import streamlit as st
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

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
    if not username or not password: return False
    if username == "testuser" and password == "password": return True
    return False

def check_page_authorization() -> None:
    try:
        page_script_path = st.get_option("client.currentPage")
    except Exception as e:
        st.error("Fatal Error: Could not determine page for authorization.")
        st.stop()

    current_page_script = os.path.basename(page_script_path)
    user_role = st.session_state.get('user_role', 'Guest')
    authorized_roles = AUTH_CONFIG["page_permissions"].get(current_page_script)

    if authorized_roles is None:
        st.error(f"Authorization Error: Page '{current_page_script}' has no security configuration.")
        st.stop()
    
    if user_role not in authorized_roles:
        st.error("🚫 Access Denied")
        st.warning(f"Your role ('{user_role}') is not authorized to view this page.")
        st.page_link("app.py", label="Return to Home", icon="🏠")
        st.stop()
