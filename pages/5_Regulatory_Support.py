# pages/5_Regulatory_Support.py

import streamlit as st
import pandas as pd
import logging

# All imports should be from the new, professional structure.
from src.veritas.ui import utils, auth

logger = logging.getLogger(__name__)

# --- UI Rendering Functions ---

def render_report_configuration(hplc_data: pd.DataFrame):
    """Renders the configuration section for the report."""
    st.header("1. Configure Report Content")
    col1, col2 = st.columns(2)
    
    with col1:
        study_options = sorted(hplc_data['study_id'].unique().tolist())
        st.selectbox("Select a Study:", options=study_options, key="selected_study")
        st.radio("Select Report Format:", options=['PDF', 'PowerPoint'], horizontal=True, key="report_format")

    with col2:
        st.write("**Select sections to include in the report:**")
        sections = {
            'include_summary_stats': st.checkbox("Summary Statistics Table", value=True, key="cfg_summary"),
            'include_cpk_analysis': st.checkbox("Process Capability Plot", value=True, key="cfg_cpk"),
            'include_full_dataset': st.checkbox("Full Dataset (Appendix)", value=False, key="cfg_fulldata"),
        }
        # Store config in session state so other functions can access it
        st.session_state.sections_config = sections

def render_commentary_and_generation(manager):
    """Renders the commentary and draft generation section."""
    st.header("2. Add Commentary & Generate")
    cpk_config = manager.settings.app.process_capability
    
    st.selectbox(
        "Select Primary CQA for Report Analysis:",
        options=cpk_config.available_cqas,
        index=0,
        key="selected_cqa"
    )
    
    default_commentary = (
        f"This report summarizes the data for study {st.session_state.selected_study}. "
        f"The primary CQA, {st.session_state.selected_cqa}, remained well within the established specification limits."
    )
    st.text_area("Enter Analyst Commentary:", default_commentary, height=100, key="commentary")

    if st.button(f"Generate DRAFT {st.session_state.report_format} Report", type="primary"):
        with st.spinner(f"Assembling DRAFT {st.session_state.report_format} report..."):
            try:
                report_df = utils.get_cached_data('hplc')
                report_df = report_df[report_df['study_id'] == st.session_state.selected_study]
                
                # Consolidate all parameters into a single dictionary
                params = {
                    'report_df': report_df, 'study_id': st.session_state.selected_study,
                    'report_format': st.session_state.report_format, 'cqa': st.session_state.selected_cqa,
                    'sections_config': st.session_state.sections_config, 'commentary': st.session_state.commentary
                }
                
                # Delegate generation to the session manager
                draft_report = manager.generate_draft_report(params)
                st.session_state.draft_report = draft_report
                st.session_state.final_report = None # Clear any old final report
                st.success(f"DRAFT {st.session_state.report_format} report generated successfully.")
            except Exception as e:
                logger.error(f"Failed to generate draft report: {e}", exc_info=True)
                st.error(f"Failed to generate draft report: {e}")

def render_signing_and_locking(manager):
    """Renders the e-signature form and final download section."""
    draft_report = st.session_state.get('draft_report')
    if not draft_report:
        st.info("Generate a draft report to proceed with signing.")
        return

    st.markdown("---")
    st.header("3. Sign & Lock Report")
    st.info(f"**Report Ready for Signature:** `{draft_report['filename']}`")
    
    st.download_button(
        label="Download DRAFT Watermarked Version for Review",
        data=draft_report['bytes'],
        file_name=draft_report['filename'],
        mime=draft_report['mime']
    )
    
    # E-signing is only available for PDF format in this implementation
    if st.session_state.report_format != 'PDF':
        st.warning("Electronic signing is only available for PDF reports.")
        return

    st.warning("⚠️ **Action Required:** This report is a **DRAFT** and is not valid for submission until it is electronically signed.")
    
    with st.form("e_signature_form"):
        st.subheader("21 CFR Part 11 Electronic Signature", anchor=False)
        st.text_input("Username", value=st.session_state.username, disabled=True)
        password_input = st.text_input("Password", type="password")
        signing_reason = st.selectbox("Reason for Signing:", options=["Author Approval", "Technical Review", "QA Final Approval"])
        
        submitted = st.form_submit_button("Sign and Lock Report")
        if submitted:
            if not password_input:
                st.error("Password is required.")
            elif not auth.verify_credentials(st.session_state.username, password_input):
                 st.error("Authentication failed. Please check your credentials.")
            else:
                with st.spinner("Applying secure signature and finalizing report..."):
                    try:
                        # Delegate finalization and signing to the session manager
                        final_report_artifact = manager.finalize_and_sign_report(
                            draft_report_data=draft_report['report_data'],
                            signing_reason=signing_reason,
                            username=st.session_state.username
                        )
                        st.session_state.final_report = final_report_artifact
                        st.session_state.draft_report = None # Clear draft after signing
                        st.success(f"Report **{final_report_artifact['filename']}** has been successfully signed and locked.")
                        st.balloons()
                    except Exception as e:
                        logger.error(f"Failed to sign and lock report: {e}", exc_info=True)
                        st.error(f"Failed to sign and lock report: {e}")

    final_report = st.session_state.get('final_report')
    if final_report:
        st.download_button(
            label=f"⬇️ Download FINAL Signed Report: {final_report['filename']}",
            data=final_report['final_bytes'],
            file_name=final_report['filename'],
            mime=final_report['mime'],
            type="primary"
        )

def main():
    """
    The main function for the page, ensuring correct initialization and flow.
    """
    try:
        manager = utils.initialize_page("Regulatory Support", "📄")

        # Initialize page-specific session state keys
        if 'draft_report' not in st.session_state:
            st.session_state.draft_report = None
        if 'final_report' not in st.session_state:
            st.session_state.final_report = None
            
        st.title("📄 Regulatory Support & Report Assembler")
        st.markdown("Compile data summaries and generate formatted, e-signed reports for submissions.")
        st.markdown("---")

        hplc_data = utils.get_cached_data('hplc')
        if hplc_data.empty:
            st.error("HPLC data could not be loaded. This page requires HPLC data to function.")
            st.stop()
        
        render_report_configuration(hplc_data)
        st.markdown("---")
        render_commentary_and_generation(manager)
        render_signing_and_locking(manager)

        auth.display_compliance_footer()

    except Exception as e:
        logger.error(f"An error occurred on the Regulatory Support page: {e}", exc_info=True)
        st.error("An unexpected error occurred. Please contact support.")


if __name__ == "__main__":
    main()
