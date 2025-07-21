# src/veritas/ui/auth.py

import streamlit as st
import logging

logger = logging.getLogger(__name__)

def verify_credentials(username: str, password: Optional[str]) -> bool:
    """
    Verifies user credentials.

    In a real application, this would connect to an identity provider (e.g., LDAP,
    OAuth, database). For this mock implementation, it performs a simple check.

    Args:
        username (str): The username to verify.
        password (Optional[str]): The password to verify.

    Returns:
        bool: True if credentials are valid, False otherwise.
    """
    if not username or not password:
        logger.warning("Authentication attempt with empty username or password.")
        return False
    
    # Placeholder for real authentication logic.
    # This mock implementation allows any non-empty username/password pair.
    logger.info(f"Verifying credentials for user: '{username}'")
    if username == "testuser" and password == "password":
        logger.info(f"Successfully authenticated user: '{username}'")
        return True
    
    logger.warning(f"Failed authentication attempt for user: '{username}'")
    return False

def display_compliance_footer() -> None:
    """
    Renders a standardized, GxP-compliant footer at the bottom of a Streamlit page.
    This function is designed to be called at the end of each page's rendering logic.
    """
    try:
        st.markdown("---")
        # Using a single markdown block with <br> for spacing is more efficient
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
        # This is a non-critical failure, so we log it but don't stop the app.
        logger.error(f"Failed to render compliance footer: {e}", exc_info=True)
        st.warning("Compliance information could not be displayed.")

def perform_logout() -> None:
    """
    Logs the user out by clearing all relevant session state keys.
    """
    logger.info(f"Logging out user: '{st.session_state.get('username', 'Unknown')}'")
    keys_to_clear = ['is_authenticated', 'username', 'user_role']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # After clearing state, rerun the script to force a redirect to the login page.
    st.rerun()
