# app.py

import streamlit as st
import logging

# All imports should be from the new, professional structure.
from src.veritas.ui import utils, auth
from src.veritas.engine import plotting

logger = logging.getLogger(__name__)

# --- UI Rendering Functions ---

def render_login_page():
    """
    Displays the login interface for unauthenticated users.
    This function has its own page config for a centered layout.
    """
    st.set_page_config(page_title="Welcome to VERITAS", page_icon="🧪", layout="centered")
    st.title("Welcome to the VERITAS Platform")
    
    with st.form("login_form"):
        # Pre-fill with mock credentials for ease of use in development
        username = st.text_input("Username", "testuser")
        password = st.text_input("Password", type="password", value="password")
        submitted = st.form_submit_button("Log In", type="primary")

        if submitted:
            if auth.verify_credentials(username, password):
                # On successful login, set session state flags and rerun
                st.session_state.is_authenticated = True
                st.session_state.username = username
                # Assign a role based on the user (mocked here)
                st.session_state.user_role = "DTE Leadership" if username == "testuser" else "Guest"
                st.rerun()
            else:
                st.error("Invalid username or password.")

def render_mission_control():
    """
    Renders the main "Mission Control" dashboard for an authenticated user.
    """
    # This call handles page config, auth, and returns the business logic controller
    manager = utils.initialize_page(page_title="Mission Control", page_icon="🏠")
    
    st.title("🏠 VERITAS Mission Control")
    st.success(f"Welcome, {st.session_state.username}! Your dashboard is ready.")

    # --- Action Items Section ---
    st.subheader("Your Mission Briefing", divider='blue')
    try:
        action_items = manager.get_user_action_items(st.session_state.user_role)
        if not action_items:
            st.success("✅ Your action item queue is clear. Well done!")
        else:
            st.warning(f"You have **{len(action_items)}** items requiring your attention.")
            for item in action_items:
                st.page_link(page=item['page_link'], label=f"**{item['title']}**: {item['details']}", icon=item['icon'])
    except Exception as e:
        logger.error(f"Failed to load action items: {e}", exc_info=True)
        st.error("Could not load your action items.")

    st.markdown("---")

    # --- Command Center Section (Role-Specific) ---
    user_role = st.session_state.user_role
    st.header(f"'{user_role}' Command Center", anchor=False)
    
    if user_role == 'DTE Leadership':
        try:
            # KPI Metrics
            kpi_cols = st.columns(4)
            kpi_names = ['active_deviations', 'data_quality_score', 'first_pass_yield', 'mean_time_to_resolution']
            for i, kpi_name in enumerate(kpi_names):
                with kpi_cols[i]:
                    kpi_data = manager.get_kpi(kpi_name)
                    st.metric(
                        label=kpi_data['sme_info'].split('.')[0], # Extract label from help text
                        value=f"{kpi_data['value']:.1f}" if isinstance(kpi_data['value'], float) else kpi_data['value'],
                        delta=f"{kpi_data['delta']:.1f}" if kpi_data.get('delta') is not None else None,
                        help=kpi_data['sme_info']
                    )

            st.markdown("---")

            # Visualizations
            viz_col1, viz_col2 = st.columns((6, 4))
            with viz_col1:
                st.subheader("Program Risk Matrix", divider='gray')
                risk_data = manager.get_risk_matrix_data()
                st.plotly_chart(plotting.plot_program_risk_matrix(risk_data), use_container_width=True)

            with viz_col2:
                st.subheader("QC Failure Hotspots", divider='gray')
                pareto_data = manager.get_pareto_data()
                st.plotly_chart(plotting.plot_pareto_chart(pareto_data, 'Error Type', 'Frequency'), use_container_width=True)

        except Exception as e:
            logger.error(f"Failed to render leadership dashboard: {e}", exc_info=True)
            st.error("Failed to load the leadership dashboard.")
    else:
        st.info("💡 Your mission-critical tools are available in the sidebar.")

    auth.display_compliance_footer()

def main():
    """
    Main function to route between the login page and the main application.
    This is the first code that runs.
    """
    # This check on st.session_state determines which view to show.
    if not st.session_state.get('is_authenticated'):
        render_login_page()
    else:
        render_mission_control()

if __name__ == "__main__":
    main()
