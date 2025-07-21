# pages/3_Process_Capability_Dashboard.py

import streamlit as st
import pandas as pd
import logging

# All imports should be from the new, professional structure.
from src.veritas.ui import utils, auth
from src.veritas.engine import analytics, plotting

logger = logging.getLogger(__name__)

# --- UI Rendering Functions ---

def render_capability_charts_tab(manager, filtered_df: pd.DataFrame, deviations_data: pd.DataFrame):
    """Renders the UI for the Capability & Control Charts tab."""
    st.header("Process Performance Analysis")
    st.info(
        """
        **Purpose:** To assess process performance over time. A process must be **stable** (in control) 
        before its **capability** can be meaningfully calculated. Use the interactive tools below to 
        monitor stability and simulate capability under different scenarios.
        """
    )
    
    cpk_config = manager.settings.app.process_capability
    
    col1, col2 = st.columns([1, 2])
    with col1:
        default_cqa_index = cpk_config.available_cqas.index('purity') if 'purity' in cpk_config.available_cqas else 0
        selected_cqa = st.selectbox(
            "Select a CQA:",
            options=cpk_config.available_cqas,
            index=default_cqa_index,
            key="cpk_cqa"
        )
    with col2:
        # Safely access spec limits from the config object
        spec_limit_info = cpk_config.spec_limits.get(selected_cqa)
        if spec_limit_info:
            default_lsl = spec_limit_info.lsl
            default_usl = spec_limit_info.usl
        else:
            default_lsl, default_usl = 0.0, 0.0
            st.warning(f"No spec limits defined for {selected_cqa} in config.")

        st.write("**Interactive Specification Limits (for 'What-If' Analysis):**")
        lsl_col, usl_col = st.columns(2)
        lsl = lsl_col.number_input("Lower Spec Limit (LSL)", value=float(default_lsl or 0.0), format="%.2f", step=0.1, key="cpk_lsl")
        usl = usl_col.number_input("Upper Spec Limit (USL)", value=float(default_usl or 0.0), format="%.2f", step=0.1, key="cpk_usl")

    if lsl is not None and usl is not None and lsl >= usl:
        st.error("Lower Specification Limit (LSL) must be less than Upper Specification Limit (USL).")
        st.stop()

    st.markdown("---")
    
    if len(filtered_df) < 3:
        st.warning("Not enough data available (minimum 3 points) for the selected filters to perform analysis.")
        return

    cpk_value = analytics.calculate_cpk(filtered_df[selected_cqa], lsl, usl)
    
    plot_col1, plot_col2 = st.columns(2)
    with plot_col1:
        st.subheader("Process Stability (Control Chart)", anchor=False)
        control_chart_fig = plotting.plot_historical_control_chart(filtered_df, selected_cqa, deviations_data)
        st.plotly_chart(control_chart_fig, use_container_width=True)
        
    with plot_col2:
        st.subheader("Process Capability (Histogram)", anchor=False)
        capability_fig = plotting.plot_process_capability(
            filtered_df, selected_cqa, lsl, usl, cpk_value, cpk_config.cpk_target
        )
        st.plotly_chart(capability_fig, use_container_width=True)


def render_anova_tab(filtered_df: pd.DataFrame, cpk_config):
    """Renders the UI for the Root Cause Analysis (ANOVA) tab."""
    st.header("Investigate Process Variation with ANOVA")
    st.info(
        """
        **Purpose:** To determine if there is a statistically significant difference between the means 
        of two or more groups. This is a powerful tool to investigate if a factor like **Instrument** 
        or **Analyst** is causing variation in your process.
        """
    )
    
    st.subheader("1. Configure ANOVA Test", anchor=False)
    col1, col2 = st.columns(2)
    with col1:
        default_cqa_index = cpk_config.available_cqas.index('purity') if 'purity' in cpk_config.available_cqas else 0
        value_col = st.selectbox("Select CQA to Analyze:", options=cpk_config.available_cqas, index=default_cqa_index, key="anova_value")
    with col2:
        group_options = ['instrument_id', 'analyst', 'batch_id']
        group_col = st.selectbox("Select Grouping Factor:", options=group_options, key="anova_group")
    
    if st.button("🔬 Run ANOVA Analysis", type="primary"):
        # Clear previous results from state
        st.session_state.anova_results, st.session_state.tukey_results = None, None
        
        if filtered_df[group_col].nunique() < 2:
            st.warning(f"Only one group found for '{group_col}'. Cannot perform ANOVA.")
        else:
            with st.spinner("Performing Analysis of Variance..."):
                anova_results = analytics.perform_anova(filtered_df, value_col, group_col)
                st.session_state.anova_results = anova_results
                
                # Run Tukey test only if ANOVA is significant and there are more than 2 groups
                if anova_results.get('p_value', 1.0) <= 0.05 and filtered_df[group_col].nunique() > 2:
                    tukey_results = analytics.perform_tukey_hsd(filtered_df, value_col, group_col)
                    st.session_state.tukey_results = tukey_results
    
    anova_results = st.session_state.get('anova_results')
    if anova_results:
        st.markdown("---")
        st.subheader("2. ANOVA Results", anchor=False)
        p_value = anova_results.get('p_value')

        if p_value is not None:
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.metric("ANOVA P-value", f"{p_value:.4f}")
                if p_value <= 0.05:
                    st.error(f"**Conclusion:** A significant difference between groups was detected.", icon="🚨")
                else:
                    st.success(f"**Conclusion:** No significant difference was detected.", icon="✅")
            with res_col2:
                st.plotly_chart(plotting.plot_anova_results(filtered_df, value_col, group_col, anova_results), use_container_width=True)
        else:
            st.error(f"ANOVA analysis failed. Reason: {anova_results.get('reason', 'Unknown')}")
    
    tukey_results = st.session_state.get('tukey_results')
    if tukey_results is not None and not tukey_results.empty:
        st.markdown("---")
        st.subheader("3. Post-Hoc Analysis (Tukey's HSD)", anchor=False)
        st.info(
            "Since the ANOVA test was significant, this test determines **exactly which groups are different** from each other. "
            "If `reject` is `True`, the difference is statistically significant."
        )
        st.dataframe(tukey_results, use_container_width=True, hide_index=True)
        
        significant_pairs = tukey_results[tukey_results['reject'] == True]
        if not significant_pairs.empty:
            pairs_text = [f"**{row['group1']}** vs **{row['group2']}**" for _, row in significant_pairs.iterrows()]
            st.error(f"**Actionable Insight:** The following pairs are significantly different: " + ", ".join(pairs_text) + ".", icon="🎯")

def main():
    """
    The main function for the page, ensuring correct initialization and flow.
    """
    try:
        manager = utils.initialize_page("Process Capability", "📈")

        if 'anova_results' not in st.session_state:
            st.session_state.anova_results = None
        if 'tukey_results' not in st.session_state:
            st.session_state.tukey_results = None

        st.title("📈 Process Capability Dashboard")
        st.markdown("Analyze historical process stability, quantify capability, and perform root cause analysis on process variation.")

        hplc_data = utils.get_cached_data('hplc')
        deviations_data = utils.get_cached_data('deviations')
        if hplc_data.empty:
            st.error("HPLC data could not be loaded. This page requires HPLC data to function.")
            st.stop()

        st.sidebar.subheader("Filter Data", divider='blue')
        study_options = sorted(hplc_data['study_id'].unique().tolist())
        if not study_options:
            st.warning("No studies available for analysis.")
            st.stop()
            
        study_filter = st.sidebar.multiselect("Filter by Study:", options=study_options, default=[study_options[0]])
        instrument_options = ['All'] + sorted(hplc_data['instrument_id'].unique().tolist())
        instrument_filter = st.sidebar.selectbox("Filter by Instrument:", options=instrument_options)

        if not study_filter:
            st.warning("Please select at least one study to begin analysis.")
            st.stop()
            
        filtered_df = hplc_data[hplc_data['study_id'].isin(study_filter)]
        if instrument_filter != 'All':
            filtered_df = filtered_df[filtered_df['instrument_id'] == instrument_filter]
        
        if filtered_df.empty:
            st.warning("No data points match the selected filters.")
            st.stop()
        st.sidebar.success(f"**{len(filtered_df)}** data points selected for analysis.")

        tab1, tab2 = st.tabs(["📊 **Capability & Control Charts**", "🔬 **Root Cause Analysis (ANOVA)**"])
        with tab1:
            render_capability_charts_tab(manager, filtered_df, deviations_data)
        with tab2:
            render_anova_tab(filtered_df, manager.settings.app.process_capability)

        auth.display_compliance_footer()
        
    except Exception as e:
        logger.error(f"An error occurred on the Process Capability Dashboard page: {e}", exc_info=True)
        st.error("An unexpected error occurred. Please contact support.")

if __name__ == "__main__":
    main()
