# pages/7_Governance_and_Audit_Hub.py

import streamlit as st
import pandas as pd
import logging
from datetime import datetime

# All imports should be from the new, professional structure.
from src.veritas.ui import utils, auth
from src.veritas.engine import plotting

logger = logging.getLogger(__name__)

# --- UI Rendering Functions ---

def render_audit_trail_tab(audit_data: pd.DataFrame):
    """Renders the UI for the Audit Trail Explorer tab."""
    st.header("Interactive Audit Trail Explorer")
    st.info("Search, filter, and export the immutable, 21 CFR Part 11-compliant audit trail for all system activities.")
    
    with st.expander("Show Filter Options", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            user_options = sorted(audit_data['user'].unique().tolist())
            users_to_filter = st.multiselect("Filter by User:", options=user_options, key="audit_user_filter")
        with col2:
            action_options = sorted(audit_data['action'].unique().tolist())
            actions_to_filter = st.multiselect("Filter by Action:", options=action_options, key="audit_action_filter")
        with col3:
            record_id_filter = st.text_input("Filter by Record ID (contains):", key="audit_record_id_filter")
    
    # Apply filters sequentially
    filtered_df = audit_data.copy()
    if users_to_filter:
        filtered_df = filtered_df[filtered_df['user'].isin(users_to_filter)]
    if actions_to_filter:
        filtered_df = filtered_df[filtered_df['action'].isin(actions_to_filter)]
    if record_id_filter:
        # Use .str.contains() for partial matching, ensuring case-insensitivity and handling of NaNs.
        filtered_df = filtered_df[filtered_df['record_id'].str.contains(record_id_filter, case=False, na=False)]
    
    st.metric("Total Records Found", f"{len(filtered_df)} of {len(audit_data)}")
    
    if filtered_df.empty:
        st.info("No audit records match the selected filters.")
    else:
        st.dataframe(filtered_df.sort_values(by='timestamp', ascending=False), use_container_width=True, hide_index=True)
        
        st.download_button(
            label="Export Filtered Results to CSV",
            data=filtered_df.to_csv(index=False).encode('utf-8'),
            file_name=f"VERITAS_Audit_Export_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            type="primary"
        )

def render_data_lineage_tab(audit_data: pd.DataFrame):
    """Renders the UI for the Visual Data Lineage tab."""
    st.header("Visual Data Lineage Tracer")
    st.info("Trace the complete history of any data record from creation to final state, providing an end-to-end, auditable map of its lifecycle.")
    
    traceable_ids = sorted(audit_data['record_id'].dropna().unique().tolist())
    
    if not traceable_ids:
        st.warning("No traceable records found in the audit log.")
        return
        
    # Set a more relevant default ID for tracing, e.g., the one with the most events
    record_counts = audit_data['record_id'].value_counts()
    default_id = record_counts.idxmax() if not record_counts.empty else traceable_ids[0]
    default_index = traceable_ids.index(default_id) if default_id in traceable_ids else 0

    record_to_trace = st.selectbox(
        "Select a Record ID to Trace:",
        options=traceable_ids,
        index=default_index,
        key="lineage_record_id"
    )
    
    if record_to_trace:
        with st.spinner("Generating lineage graph..."):
            try:
                lineage_graph = plotting.plot_data_lineage_graph(audit_data, record_to_trace)
                st.graphviz_chart(lineage_graph)
            except Exception as e:
                logger.error(f"Failed to generate lineage graph for {record_to_trace}: {e}", exc_info=True)
                st.error(f"Could not display data lineage graph: {e}")

def render_signature_log_tab(manager):
    """Renders the UI for the Electronic Signature Log tab."""
    st.header("Electronic Signature Log")
    st.info("A live, filtered view of all electronic signature events, demonstrating compliance with 21 CFR Part 11.")
    
    signature_log_df = manager.get_signatures_log()
    
    if signature_log_df.empty:
        st.success("No electronic signature events have been recorded yet.")
    else:
        display_cols = ['timestamp', 'user', 'action', 'record_id', 'details']
        st.dataframe(
            signature_log_df[display_cols].sort_values(by='timestamp', ascending=False),
            use_container_width=True,
            hide_index=True
        )

def main():
    """
    The main function for the page, ensuring correct initialization and flow.
    """
    try:
        manager = utils.initialize_page("Governance & Audit Hub", "⚖️")

        st.title("⚖️ Governance & Audit Hub")
        st.markdown("Central hub for 21 CFR Part 11 compliance, data lineage, and system audit trails.")

        audit_data = utils.get_cached_data('audit')
        if audit_data.empty:
            st.error("Audit data could not be loaded. This page requires audit data to function.")
            st.stop()
            
        tab1, tab2, tab3 = st.tabs(["🔍 **Audit Trail Explorer**", "🧬 **Visual Data Lineage**", "✍️ **E-Signature Log**"])

        with tab1:
            render_audit_trail_tab(audit_data)
        with tab2:
            render_data_lineage_tab(audit_data)
        with tab3:
            render_signature_log_tab(manager)
            
        auth.display_compliance_footer()
        
    except Exception as e:
        logger.error(f"An error occurred on the Governance & Audit Hub page: {e}", exc_info=True)
        st.error("An unexpected error occurred. Please contact support.")


if __name__ == "__main__":
    main()
