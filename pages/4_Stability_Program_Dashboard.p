# pages/4_Stability_Program_Dashboard.py

import streamlit as st
import pandas as pd
import logging

# All imports should be from the new, professional structure.
from src.veritas.ui import utils, auth
from src.veritas.engine import analytics, plotting

logger = logging.getLogger(__name__)

# --- UI Rendering Functions ---

def render_poolability_assessment(filtered_df: pd.DataFrame, stability_config):
    """
    Performs and displays the results of the ANCOVA poolability test.
    Stores the results in st.session_state for use by other functions.
    """
    st.header("Multi-Lot Poolability Assessment (ANCOVA)")
    st.info(
        """
        According to ICH Q1E guidelines, a statistical test (ANCOVA) can determine if data 
        from different stability lots can be combined. This is permissible only if the regression 
        lines (slopes) for each lot are not statistically different (p > 0.05).
        """
    )
    
    # Reset state before running
    st.session_state.poolability_results = {}
    
    assays_to_test = [assay for assay in stability_config.spec_limits.keys() if assay in filtered_df.columns]
    
    if not assays_to_test:
        st.warning("No valid assays (e.g., 'purity', 'main_impurity') found in the data for poolability analysis.")
        return

    with st.spinner("Performing ANCOVA tests for lot poolability..."):
        for assay in assays_to_test:
            try:
                result = analytics.test_stability_poolability(filtered_df, assay)
                st.session_state.poolability_results[assay] = result
            except Exception as e:
                logger.error(f"ANCOVA test failed for assay '{assay}': {e}", exc_info=True)
                st.session_state.poolability_results[assay] = {'poolable': False, 'reason': f'Test failed: {e}'}

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Purity Poolability")
        purity_result = st.session_state.poolability_results.get('purity', {})
        if purity_result:
            st.metric("Interaction P-value", f"{purity_result.get('p_value', 0.0):.3f}")
            if purity_result.get('poolable'):
                st.success("Purity data from these lots can be pooled.", icon="✅")
            else:
                st.warning("Purity data from these lots should NOT be pooled.", icon="⚠️")
        else:
            st.info("No poolability results available for purity.")

    with col2:
        st.subheader("Main Impurity Poolability")
        impurity_result = st.session_state.poolability_results.get('main_impurity', {})
        if impurity_result:
            st.metric("Interaction P-value", f"{impurity_result.get('p_value', 0.0):.3f}")
            if impurity_result.get('poolable'):
                st.success("Impurity data from these lots can be pooled.", icon="✅")
            else:
                st.warning("Impurity data from these lots should NOT be pooled.", icon="⚠️")
        else:
            st.info("No poolability results available for main impurity.")

def render_stability_profile(filtered_df: pd.DataFrame, stability_config):
    """
    Displays the stability trend charts for Purity and Main Impurity.
    """
    product_filter = filtered_df['product_id'].iloc[0]
    lot_filter = filtered_df['lot_id'].unique()
    
    st.header(f"Stability Profile for {product_filter} - Lot(s): {', '.join(lot_filter)}")
    poolability_results = st.session_state.get('poolability_results', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        assay_purity = 'purity'
        if assay_purity in stability_config.spec_limits and assay_purity in filtered_df.columns:
            # Pooled data can only be used if there are multiple lots and the test passes
            use_pooled_purity = len(lot_filter) > 1 and poolability_results.get(assay_purity, {}).get('poolable', False)
            title = f"Purity Trend {'(Pooled)' if use_pooled_purity else '(Separate Lots)'}"
            
            projection = analytics.calculate_stability_projection(filtered_df, assay_purity, use_pooled_purity)
            fig = plotting.plot_stability_trend(filtered_df, assay_purity, title, stability_config.spec_limits[assay_purity], projection)
            st.plotly_chart(fig, use_container_width=True)
            
            if projection:
                st.metric("Trend Slope", f"{projection.get('slope', 0.0):.3f} / month", help="Linear regression slope.")
        else:
            st.info("Purity data or specification limits not available for trend analysis.")

    with col2:
        assay_impurity = 'main_impurity'
        if assay_impurity in stability_config.spec_limits and assay_impurity in filtered_df.columns:
            # Pooled data can only be used if there are multiple lots and the test passes
            use_pooled_impurity = len(lot_filter) > 1 and poolability_results.get(assay_impurity, {}).get('poolable', False)
            title = f"Main Impurity Trend {'(Pooled)' if use_pooled_impurity else '(Separate Lots)'}"
            
            projection = analytics.calculate_stability_projection(filtered_df, assay_impurity, use_pooled_impurity)
            fig = plotting.plot_stability_trend(filtered_df, assay_impurity, title, stability_config.spec_limits[assay_impurity], projection)
            st.plotly_chart(fig, use_container_width=True)
            
            if projection:
                st.metric("Trend Slope", f"+{projection.get('slope', 0.0):.3f} / month", help="Linear regression slope.")
        else:
            st.info("Main Impurity data or specification limits not available for trend analysis.")

def main():
    """
    The main function for the page, ensuring correct initialization and flow.
    """
    try:
        manager = utils.initialize_page("Stability Dashboard", "⏳")
        
        if 'poolability_results' not in st.session_state:
            st.session_state.poolability_results = {}

        st.title("⏳ Stability Program Dashboard")
        st.markdown("Monitor stability data, project shelf-life with statistical confidence, and perform multi-lot poolability analysis for regulatory submissions.")

        stability_data = utils.get_cached_data('stability')
        if stability_data.empty:
            st.error("Stability data could not be loaded. This page requires stability data to function.")
            st.stop()

        st.sidebar.subheader("Select Stability Study", divider='blue')
        product_options = sorted(stability_data['product_id'].unique().tolist())
        if not product_options:
            st.warning("No products available for analysis.")
            st.stop()

        product_filter = st.sidebar.selectbox("Select Product:", options=product_options, key="stability_product")
        
        lot_options = sorted(stability_data[stability_data['product_id'] == product_filter]['lot_id'].unique().tolist())
        if not lot_options:
            st.warning(f"No lots available for product '{product_filter}'.")
            st.stop()
            
        lot_filter = st.sidebar.multiselect(
            "Select Lot(s):", options=lot_options, default=lot_options,
            help="Select multiple lots to perform a poolability analysis.", key="stability_lots"
        )

        if not lot_filter:
            st.warning("Please select at least one lot to begin analysis.")
            st.stop()

        filtered_df = stability_data[
            (stability_data['product_id'] == product_filter) & 
            (stability_data['lot_id'].isin(lot_filter))
        ].copy() # Use .copy() to avoid SettingWithCopyWarning
        
        if filtered_df.empty:
            st.warning("No stability data available for the selected product and lot combination.")
            st.stop()

        st.markdown("---")
        
        # Only render the poolability assessment if more than one lot is selected.
        if len(lot_filter) > 1:
            render_poolability_assessment(filtered_df, manager.settings.app.stability_specs)
            st.markdown("---")
        else:
            # If only one lot, ensure poolability results are cleared so plots don't show "Pooled"
            st.session_state.poolability_results = {}


        render_stability_profile(filtered_df, manager.settings.app.stability_specs)

        with st.expander("Show Raw Stability Data for Selected Lots"):
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        auth.display_compliance_footer()

    except Exception as e:
        logger.error(f"An error occurred on the Stability Program Dashboard page: {e}", exc_info=True)
        st.error("An unexpected error occurred. Please contact support.")

if __name__ == "__main__":
    main()
