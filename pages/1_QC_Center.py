# pages/1_QC_Center.py

import streamlit as st
import pandas as pd
import numpy as np
import logging

# All imports should be from the new, professional structure.
from src.veritas.ui import utils, auth
from src.veritas.engine import analytics, plotting

logger = logging.getLogger(__name__)

# --- UI Rendering Functions ---
# Breaking the UI into smaller, manageable functions improves readability and maintainability.

def render_rule_based_qc_tab(manager, selected_df: pd.DataFrame):
    """Renders the UI for the Rule-Based QC Engine tab."""
    st.header("Automated Rule-Based Quality Control")
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("1. Configure QC Rules", anchor=False)
        with st.form("qc_rules_form"):
            rules_config = {
                'check_nulls': st.checkbox("Check for critical missing values", value=True),
                'check_negatives': st.checkbox("Check for impossible negative values (bio_activity)", value=True),
                'check_spec_limits': st.checkbox("Check against CQA specifications", value=True),
            }
            submitted = st.form_submit_button("▶️ Execute QC Analysis", type="primary")
        
        if submitted:
            with st.spinner("Running QC checks..."):
                try:
                    report = analytics.apply_qc_rules(
                        df=selected_df,
                        rules_config=rules_config,
                        app_config=manager.settings.app
                    )
                    st.session_state.qc_report = report
                    st.success("QC analysis complete.")
                except Exception as e:
                    logger.error(f"QC analysis failed: {e}", exc_info=True)
                    st.error(f"Failed to execute QC analysis: {e}")

    with col2:
        st.subheader("2. Review QC Results", anchor=False)
        report_df = st.session_state.get('qc_report')

        if report_df is None:
            st.info("Configure and execute QC analysis to see results.")
        elif report_df.empty:
            st.success("✅ Congratulations! No rule-based discrepancies were found.")
        else:
            st.metric("Discrepancies Found", len(report_df))
            st.error(f"Found **{len(report_df)}** issues requiring attention.")
            st.dataframe(report_df, use_container_width=True, hide_index=True)
            
            st.subheader("3. Take Action", anchor=False)
            if st.button("Create Deviation Ticket from Results", type="secondary"):
                try:
                    new_dev_id = manager.create_deviation_from_qc(
                        report_df=report_df,
                        study_id=selected_df['study_id'].iloc[0],
                        username=st.session_state.username
                    )
                    st.success(f"Successfully created a new deviation ticket: **{new_dev_id}**.")
                    st.info("You can view this ticket in the Deviation Hub.")
                    st.session_state.qc_report = None # Clear the report
                except Exception as e:
                    logger.error(f"Failed to create deviation ticket: {e}", exc_info=True)
                    st.error(f"Failed to create deviation ticket: {e}")


def render_statistical_dive_tab(selected_df: pd.DataFrame):
    """Renders the UI for the Statistical Deep Dive tab."""
    st.header("Statistical Deep Dive")
    numeric_cols = selected_df.select_dtypes(include=np.number).columns.tolist()
    
    if not numeric_cols:
        st.warning("No numeric columns available for statistical analysis in this dataset.")
        return

    default_index = numeric_cols.index('purity') if 'purity' in numeric_cols else 0
    param = st.selectbox("Select Parameter", options=numeric_cols, index=default_index, key="stat_param")
    data_to_test = selected_df[param].dropna()

    if data_to_test.empty:
        st.warning(f"No valid data available for parameter '{param}'.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Shapiro-Wilk Normality Test", anchor=False)
        normality_results = analytics.perform_normality_test(data_to_test)
        if 'p_value' in normality_results and normality_results['p_value'] is not None:
            st.metric("P-value", f"{normality_results['p_value']:.4f}")
            if normality_results['p_value'] > 0.05:
                st.success(f"Conclusion: {normality_results['conclusion']}")
            else:
                st.warning(f"Conclusion: {normality_results['conclusion']}")
        else:
            st.info(normality_results.get('conclusion', 'Could not perform test.'))
            
        st.subheader("Descriptive Statistics", anchor=False)
        st.dataframe(data_to_test.describe().round(3), use_container_width=True)

    with col2:
        st.subheader("Quantile-Quantile (Q-Q) Plot", anchor=False)
        st.plotly_chart(plotting.plot_qq(data_to_test), use_container_width=True)


def render_ml_anomaly_tab(selected_df: pd.DataFrame):
    """Renders the UI for the ML Anomaly Detection tab."""
    st.header("Machine Learning-Powered Anomaly Detection")
    numeric_cols = selected_df.select_dtypes(include=np.number).columns.tolist()

    if len(numeric_cols) < 3:
        st.warning("This dataset requires at least 3 numeric columns for 3D ML anomaly detection.")
        return

    with st.form("ml_anomaly_form"):
        st.subheader("Configure Anomaly Detection", anchor=False)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            x_col = st.selectbox("X-axis", numeric_cols, index=numeric_cols.index('purity') if 'purity' in numeric_cols else 0)
        with c2:
            y_col = st.selectbox("Y-axis", numeric_cols, index=numeric_cols.index('bio_activity') if 'bio_activity' in numeric_cols else 1)
        with c3:
            z_col = st.selectbox("Z-axis", numeric_cols, index=numeric_cols.index('main_impurity') if 'main_impurity' in numeric_cols else 2)
        with c4:
            contamination = st.slider("Sensitivity", 0.01, 0.2, 0.05, 0.01, help="Higher values will flag more points as anomalies.")
        
        ml_submitted = st.form_submit_button("🤖 Find Anomalies", type="primary")

    if ml_submitted:
        cols_to_use = [x_col, y_col, z_col]
        if len(set(cols_to_use)) != 3:
            st.error("Please select three unique variables for the axes.")
        else:
            with st.spinner("Running anomaly detection model..."):
                predictions, data_fitted = analytics.run_anomaly_detection(selected_df, cols_to_use, contamination)
                st.session_state.ml_results = {'preds': predictions, 'data': data_fitted, 'cols': cols_to_use}

    ml_results = st.session_state.get('ml_results')
    if ml_results:
        st.plotly_chart(plotting.plot_ml_anomaly_results_3d(df=ml_results['data'], cols=ml_results['cols'], labels=ml_results['preds']), use_container_width=True)
        anomaly_count = (ml_results['preds'] == -1).sum()
        st.success(f"Analysis complete. Found **{anomaly_count}** potential anomalies (shown in red).")


def main():
    """
    The main function for the page, ensuring correct initialization and flow.
    """
    # ARCHITECTURAL FIX: All page logic is inside main().
    # The call to initialize_page handles everything: page config, login check, and role authorization.
    try:
        manager = utils.initialize_page("QC & Integrity Center", "🧪")

        # Initialize page-specific state directly in st.session_state
        if 'qc_report' not in st.session_state:
            st.session_state.qc_report = None
        if 'ml_results' not in st.session_state:
            st.session_state.ml_results = None

        st.title("🧪 QC & Integrity Center")
        st.markdown("A suite of advanced tools for data quality validation and anomaly detection.")
        
        # --- Data Loading & Filtering ---
        hplc_data = utils.get_cached_data('hplc')
        if hplc_data.empty:
            st.error("HPLC data could not be loaded. This page requires HPLC data to function.")
            st.stop()

        st.sidebar.subheader("Data Selection", divider='blue')
        study_id_options = sorted(hplc_data['study_id'].unique())
        if not study_id_options:
            st.warning("No studies available for analysis.")
            st.stop()
        
        study_id = st.sidebar.selectbox("Select Study for QC", options=study_id_options, key="qc_study_id")
        selected_df = hplc_data[hplc_data['study_id'] == study_id]
        
        if selected_df.empty:
            st.warning(f"No data points available for study '{study_id}'.")
            st.stop()
        st.sidebar.info(f"**{len(selected_df)}** data points loaded for study **'{study_id}'**.")
        
        # --- Tabbed Interface ---
        tab1, tab2, tab3 = st.tabs(["📋 **Rule-Based QC**", "📊 **Statistical Deep Dive**", "🤖 **ML Anomaly Detection**"])
        
        with tab1:
            render_rule_based_qc_tab(manager, selected_df)
        with tab2:
            render_statistical_dive_tab(selected_df)
        with tab3:
            render_ml_anomaly_tab(selected_df)
        
        auth.display_compliance_footer()

    except Exception as e:
        logger.error(f"An error occurred on the QC & Integrity Center page: {e}", exc_info=True)
        st.error("An unexpected error occurred. Please contact support.")


# This ensures the main function is called when the page is run.
if __name__ == "__main__":
    main()
