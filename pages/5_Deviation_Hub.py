# pages/5_Deviation_Hub.py

import streamlit as st
from src.veritas.ui import utils, auth
import logging

logger = logging.getLogger(__name__)

# --- UI Rendering Functions ---

def render_detail_view(manager, dev_id):
    """Renders the investigation pane for a single deviation."""
    st.title(f"📌 Investigation: {dev_id}")
    if st.button("⬅️ Back to Kanban Board"):
        st.session_state.selected_dev_id = None
        st.rerun()

    dev_details = manager.get_deviation_details(dev_id)
    if dev_details.empty:
        st.error(f"Could not load details for deviation {dev_id}.")
        return

    # ... (Logic from the original file's detail view, now cleaner)
    # Example:
    dev = dev_details.iloc[0]
    st.metric("Status", dev['status'])
    st.write(f"**Title:** {dev['title']}")
    # ... tabs for RCA, CAPA, etc. ...

def render_kanban_view(manager, dev_config):
    """Renders the main Kanban board of all deviations."""
    st.title("📌 Deviation Management Hub")
    st.markdown("An interactive Kanban board to manage the lifecycle of quality events.")
    
    kanban_cols = st.columns(len(dev_config.kanban_states))
    deviations_df = utils.get_cached_data('deviations')

    for i, status in enumerate(dev_config.kanban_states):
        with kanban_cols[i]:
            cards = deviations_df[deviations_df['status'] == status]
            st.subheader(f"{status} ({len(cards)})", anchor=False)
            st.markdown("---")
            for _, card_data in cards.iterrows():
                # ... (Logic from original file to display cards and buttons)
                # Example:
                if st.button("Investigate", key=f"inv_{card_data['id']}"):
                    st.session_state.selected_dev_id = card_data['id']
                    st.rerun()

# --- Main Page Logic ---
def main():
    # Centralized, cached, and authenticated session start
    manager = utils.initialize_page("Deviation Hub", "📌")
    
    # Initialize page-specific state directly
    if 'selected_dev_id' not in st.session_state:
        st.session_state.selected_dev_id = None

    # Routing logic based on state
    if st.session_state.selected_dev_id:
        render_detail_view(manager, st.session_state.selected_dev_id)
    else:
        dev_config = manager.settings.app.deviation_management
        render_kanban_view(manager, dev_config)

    auth.display_compliance_footer()

if __name__ == "__main__":
    main()
