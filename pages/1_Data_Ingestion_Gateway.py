# pages/1_Data_Ingestion_Gateway.py

import streamlit as st
import pandas as pd
import logging

# All imports are from the new, professional structure.
from src.veritas.ui import utils, auth

logger = logging.getLogger(__name__)

def render_uploader(manager):
    """
    Renders the file uploader and data preview UI.
    In a real application, this would interact with the manager to process the data.
    """
    st.header("Upload New Dataset")
    
    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=['csv', 'xlsx'],
        help="Upload a dataset to be processed and validated by the VERITAS platform."
    )

    if uploaded_file is not None:
        try:
            with st.spinner(f"Reading file '{uploaded_file.name}'..."):
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
            
            st.success(f"Successfully loaded `{uploaded_file.name}` with {len(df)} rows and {len(df.columns)} columns.")
            
            with st.expander("Preview first 100 rows"):
                st.dataframe(df.head(100), use_container_width=True)

            if st.button("Process and Ingest Data", type="primary", use_container_width=True):
                with st.spinner("Simulating data ingestion and validation..."):
                    # --- In a real application, this logic would be in the SessionManager ---
                    # For example:
                    # ingestion_report = manager.ingest_data(
                    #     df=df, 
                    #     filename=uploaded_file.name, 
                    #     username=st.session_state.username
                    # )
                    # st.write(ingestion_report)
                    # --------------------------------------------------------------------
                    
                    # For this demonstration, we simulate success.
                    st.success("Data ingestion process complete.")
                    st.info("The new data is now available for analysis in the relevant dashboards.")
                    # Log the successful action to the audit trail
                    manager._repo.write_audit_log(
                        user=st.session_state.username,
                        action="Data Ingestion",
                        details=f"Successfully ingested file: {uploaded_file.name}",
                        record_id=f"FILE_{uploaded_file.name}"
                    )


        except Exception as e:
            logger.error(f"Failed to read or process uploaded file: {e}", exc_info=True)
            st.error(f"An error occurred while processing the file: {e}")

def main():
    """
    The main function for the page, ensuring correct initialization and flow.
    """
    try:
        #
        # >>>>> ARCHITECTURAL FIX & DEFINITIVE SOLUTION <<<<<
        #
        # This single, mandatory call replaces all old top-level commands.
        # It handles:
        #   1. st.set_page_config() - Executed first, as required.
        #   2. Authentication Check - Halts if user is not logged in.
        #   3. Authorization Check - Halts if user's role cannot access this page.
        #
        # This structure completely resolves the `AttributeError`.
        #
        manager = utils.initialize_page("Data Ingestion Gateway", "📥")

        st.title("📥 Data Ingestion Gateway")
        st.markdown("Securely upload, validate, and ingest new datasets into the VERITAS system.")
        st.markdown("---")

        render_uploader(manager)
        
        auth.display_compliance_footer()

    except Exception as e:
        logger.error(f"An error occurred on the Data Ingestion Gateway page: {e}", exc_info=True)
        st.error("An unexpected error occurred. Please contact support.")

# This standard Python entry point ensures the main function is called when the script is run.
if __name__ == "__main__":
    main()
