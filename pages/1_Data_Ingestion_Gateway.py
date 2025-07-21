# pages/1_Data_Ingestion_Gateway.py

import streamlit as st
import pandas as pd
import logging

# All imports should be from the new, professional structure.
from src.veritas.ui import utils, auth

logger = logging.getLogger(__name__)

def render_uploader():
    """Renders the file uploader and data preview UI."""
    st.header("Upload New Dataset")
    
    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=['csv', 'xlsx'],
        help="Upload a dataset to be processed by the VERITAS platform."
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"Successfully loaded `{uploaded_file.name}` with {len(df)} rows.")
            
            with st.expander("Preview first 100 rows"):
                st.dataframe(df.head(100), use_container_width=True)

            if st.button("Process and Ingest Data", type="primary"):
                with st.spinner("Simulating data ingestion and validation..."):
                    # In a real app, this would call a manager method to handle the backend logic
                    # manager.ingest_data(df, uploaded_file.name, st.session_state.username)
                    st.success("Data ingestion process complete.")
                    st.info("The new data is now available for analysis in the relevant dashboards.")

        except Exception as e:
            logger.error(f"Failed to read or process uploaded file: {e}", exc_info=True)
            st.error(f"An error occurred while processing the file: {e}")

def main():
    """
    The main function for the page, ensuring correct initialization and flow.
    """
    try:
        # ARCHITECTURAL FIX: This single call handles all page setup and security.
        manager = utils.initialize_page("Data Ingestion Gateway", "📥")

        st.title("📥 Data Ingestion Gateway")
        st.markdown("Securely upload, validate, and ingest new datasets into the VERITAS system.")
        st.markdown("---")

        render_uploader()
        
        auth.display_compliance_footer()

    except Exception as e:
        logger.error(f"An error occurred on the Data Ingestion Gateway page: {e}", exc_info=True)
        st.error("An unexpected error occurred. Please contact support.")

# This ensures the main function is called when the page is run.
if __name__ == "__main__":
    main()
