# app.py

import streamlit as st
from src.veritas.ui import utils, auth

def render_login_page():
    """Displays the login interface for unauthenticated users."""
    st.set_page_config(page_title="Welcome to VERITAS", page_icon="🧪", layout="centered")
    st.title("Welcome to the VERITAS Platform")
    
    with st.form("login_form"):
        username = st.text_input("Username", "testuser")
        password = st.text_input("Password", type="password", value="password")
        submitted = st.form_submit_button("Log In", type="primary")

        if submitted:
            if auth.verify_credentials(username, password):
                st.session_state.is_authenticated = True
                st.session_state.username = username
                st.session_state.user_role = "DTE Leadership" # Example role
                st.rerun()
            else:
                st.error("Invalid username or password.")

def render_mission_control():
    """Renders the main dashboard for an authenticated user."""
    manager = utils.initialize_page(page_title="Mission Control", page_icon="🏠")
    st.title("🏠 VERITAS Mission Control")

    # The logic from the original 0_..._Home.py would be here, broken into smaller
    # functions that call utils.get_cached_data() for performance.
    st.success(f"Welcome, {st.session_state.username}! Your dashboard is ready.")
    
    st.subheader("Your Mission Briefing", divider='blue')
    action_items = manager.get_user_action_items(st.session_state.user_role)
    if not action_items:
        st.success("✅ Your action item queue is clear. Well done!")
    # ... more action item logic ...
    
    st.header(f"'{st.session_state.user_role}' Command Center", anchor=False)
    # ... KPI and charting logic ...

    auth.display_compliance_footer()


# --- Main Application Logic ---
def main():
    """Main function to route between login and the main app."""
    if not st.session_state.get('is_authenticated'):
        render_login_page()
    else:
        render_mission_control()

if __name__ == "__main__":
    main()
