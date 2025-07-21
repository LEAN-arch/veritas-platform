# pages/5_Deviation_Hub.py

import streamlit as st
import pandas as pd
import logging
from datetime import date

# All imports should be from the new, professional structure.
from src.veritas.ui import utils, auth

logger = logging.getLogger(__name__)

# --- UI Rendering Functions ---

def render_detail_view(manager, dev_id: str):
    """Renders the investigation pane for a single deviation."""
    st.title(f"📌 Investigation: {dev_id}")
    if st.button("⬅️ Back to Kanban Board"):
        st.session_state.selected_dev_id = None
        st.rerun()

    dev_details = manager.get_deviation_details(dev_id)
    if dev_details.empty:
        st.error(f"Could not load details for deviation {dev_id}. It may have been deleted or archived.")
        return

    dev = dev_details.iloc[0]
    
    detail_tab, data_tab, rca_tab, capa_tab = st.tabs(["📝 Details", "🔗 Linked Data", "🔎 RCA", "🛠️ CAPA"])

    with detail_tab:
        st.metric("Status", dev['status'])
        st.write(f"**Title:** {dev['title']}")
        st.write(f"**Priority:** {dev['priority']}")
        st.write(f"**Linked Record:** `{dev['linked_record']}`")

    with data_tab:
        st.subheader("Data Associated with this Deviation", anchor=False)
        linked_record = dev['linked_record']
        hplc_data = utils.get_cached_data('hplc')
        
        sample_match = hplc_data[hplc_data['sample_id'] == linked_record]
        instrument_match = hplc_data[hplc_data['instrument_id'] == linked_record]
        
        if not sample_match.empty:
            st.dataframe(sample_match, use_container_width=True, hide_index=True)
        elif not instrument_match.empty:
            st.dataframe(instrument_match.head(), use_container_width=True, hide_index=True)
            st.info(f"Showing first 5 records related to instrument {linked_record}.")
        else:
            st.info("No structured data is directly linked to this record ID.")
    
    with rca_tab:
        st.subheader("Root Cause Analysis Documentation", anchor=False)
        with st.form("rca_form"):
            rca_problem = st.text_area("Problem Statement:", value=dev.get('rca_problem', ''), height=100)
            rca_5whys = st.text_area("5 Whys Analysis:", height=150, value=dev.get('rca_5whys', ''))
            rca_submitted = st.form_submit_button("💾 Save RCA")
            if rca_submitted:
                # In a real app, this would call a manager method to update the backend
                # manager.update_deviation_rca(dev_id, rca_problem, rca_5whys)
                st.success("RCA details saved.")

    with capa_tab:
        st.subheader("Corrective and Preventive Action (CAPA) Plan", anchor=False)
        with st.form("capa_form"):
            capa_corrective = st.text_area("Corrective Action(s):", value=dev.get('capa_corrective', ''))
            capa_preventive = st.text_area("Preventive Action(s):", value=dev.get('capa_preventive', ''))
            capa_date = st.date_input("Target Completion Date:", value=date.today())
            capa_submitted = st.form_submit_button("💾 Save CAPA Plan")
            if capa_submitted:
                # In a real app, this would call a manager method to update the backend
                # manager.update_deviation_capa(...)
                st.success("CAPA plan saved.")

def render_kanban_view(manager, dev_config):
    """Renders the main Kanban board of all deviations."""
    st.title("📌 Deviation Management Hub")
    st.markdown("An interactive Kanban board to manage the lifecycle of quality events.")
    
    kanban_cols = st.columns(len(dev_config.kanban_states))
    deviations_df = utils.get_cached_data('deviations')

    for i, status in enumerate(dev_config.kanban_states):
        with kanban_cols[i]:
            cards_in_column = deviations_df[deviations_df['status'] == status]
            st.subheader(f"{status} ({len(cards_in_column)})", anchor=False)
            st.markdown("---")
            
            if cards_in_column.empty:
                st.info(f"No deviations in this status.")
            
            for _, card in cards_in_column.iterrows():
                card_id = card['id']
                with st.container(border=True):
                    st.markdown(f"**{card_id}**: {card['title']}")
                    st.markdown(f"**Priority:** {card['priority']}")
                    st.markdown(f"**Linked Record:** `{card['linked_record']}`")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Investigate", key=f"open_{card_id}", use_container_width=True):
                            st.session_state.selected_dev_id = card_id
                            st.rerun()
                    with c2:
                        if status != dev_config.kanban_states[-1]:
                            if st.button("▶️ Advance", key=f"adv_{card_id}", help=f"Move to next stage", use_container_width=True):
                                try:
                                    manager.advance_deviation_status(
                                        dev_id=card_id,
                                        current_status=status,
                                        username=st.session_state.username
                                    )
                                    st.rerun()
                                except Exception as e:
                                    logger.error(f"Failed to advance deviation {card_id}: {e}", exc_info=True)
                                    st.error(f"Failed to advance deviation: {e}")

def main():
    """
    The main function for the page, ensuring correct initialization and flow.
    """
    try:
        manager = utils.initialize_page("Deviation Hub", "📌")
        
        if 'selected_dev_id' not in st.session_state:
            st.session_state.selected_dev_id = None

        if st.session_state.selected_dev_id:
            render_detail_view(manager, st.session_state.selected_dev_id)
        else:
            dev_config = manager.settings.app.deviation_management
            render_kanban_view(manager, dev_config)

        auth.display_compliance_footer()
        
    except Exception as e:
        logger.error(f"An error occurred on the Deviation Hub page: {e}", exc_info=True)
        st.error("An unexpected error occurred. Please contact support.")


if __name__ == "__main__":
    main()
