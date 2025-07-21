# tests/test_analytics.py

import pandas as pd
import numpy as np
import pytest

# The sys.path hack is no longer needed. Imports are now direct and clean.
from veritas.engine import analytics

# --- Tests for calculate_cpk ---

def test_calculate_cpk_normal_process():
    """Test Cpk calculation with a highly capable, centered process."""
    data = pd.Series([9.9, 10.0, 10.1, 9.8, 10.2, 9.95, 10.05])
    lsl, usl = 9.5, 10.5
    # For this data, mean is ~10.0, std is ~0.13. Cpk should be well above 1.33
    cpk = analytics.calculate_cpk(data, lsl, usl)
    assert cpk > 1.33
    assert isinstance(cpk, float)

def test_calculate_cpk_off_center_process():
    """Test Cpk calculation with a process shifted towards a specification limit."""
    data = pd.Series([9.6, 9.7, 9.55, 9.65, 9.75])
    lsl, usl = 9.5, 10.5
    # Process is close to LSL, so Cpk should be low (less than 1.0)
    cpk = analytics.calculate_cpk(data, lsl, usl)
    assert cpk < 1.0

def test_calculate_cpk_with_single_sided_usl():
    """Test Cpk calculation when only an Upper Specification Limit is provided."""
    data = pd.Series([10, 11, 12, 10.5, 11.5])
    lsl, usl = None, 15.0
    # Cpl should be infinite, so Cpk must equal Cpu
    cpu = (15.0 - data.mean()) / (3 * data.std())
    cpk = analytics.calculate_cpk(data, lsl, usl)
    assert cpk == pytest.approx(cpu)

def test_calculate_cpk_with_single_sided_lsl():
    """Test Cpk calculation when only a Lower Specification Limit is provided."""
    data = pd.Series([10, 11, 12, 10.5, 11.5])
    lsl, usl = 5.0, None
    # Cpu should be infinite, so Cpk must equal Cpl
    cpl = (data.mean() - 5.0) / (3 * data.std())
    cpk = analytics.calculate_cpk(data, lsl, usl)
    assert cpk == pytest.approx(cpl)

def test_calculate_cpk_edge_cases():
    """Test edge cases like empty data, insufficient data, or zero standard deviation."""
    assert analytics.calculate_cpk(pd.Series([]), 0, 10) == 0.0
    assert analytics.calculate_cpk(pd.Series([5.0]), 0, 10) == 0.0 # Insufficient data
    assert analytics.calculate_cpk(pd.Series([5, 5, 5]), 0, 10) == 0.0 # Zero std dev

# --- Tests for ANOVA and Post-Hoc (Tukey's HSD) ---

def test_perform_anova_with_significant_difference():
    """Test ANOVA where a significant difference between groups clearly exists."""
    df = pd.DataFrame({
        'value': [10, 11, 10.5, 10.2,  20, 21, 20.5, 20.8], # Group B is much higher
        'group': ['A', 'A', 'A', 'A',   'B', 'B', 'B', 'B']
    })
    results = analytics.perform_anova(df, 'value', 'group')
    assert 'p_value' in results
    assert results['p_value'] < 0.05 # Expect a significant result

def test_perform_anova_with_no_significant_difference():
    """Test ANOVA where there is no significant difference between groups."""
    df = pd.DataFrame({
        'value': [10, 11, 10.5, 10.2,  10.1, 10.9, 10.6, 10.3], # Groups are similar
        'group': ['A', 'A', 'A', 'A',   'B', 'B', 'B', 'B']
    })
    results = analytics.perform_anova(df, 'value', 'group')
    assert 'p_value' in results
    assert results['p_value'] > 0.05 # Expect a non-significant result

def test_perform_tukey_hsd_on_mock_data(hplc_data):
    """
    Test the Tukey HSD function using realistic mock data from the fixture.
    This serves as an integration test for the function.
    """
    # The mock data was specifically designed so HPLC-03 has a purity drift
    results = analytics.perform_tukey_hsd(hplc_data, 'purity', 'instrument_id')
    
    assert isinstance(results, pd.DataFrame)
    assert 'reject' in results.columns
    
    # Check that it correctly found a significant difference between HPLC-03 (with drift) and HPLC-01 (normal)
    hplc03_vs_hplc01 = results[
        ((results.group1 == 'HPLC-01') & (results.group2 == 'HPLC-03')) |
        ((results.group1 == 'HPLC-03') & (results.group2 == 'HPLC-01'))
    ]
    assert not hplc03_vs_hplc01.empty
    assert hplc03_vs_hplc01['reject'].iloc[0] is True # Note: checking `is True` is more explicit than `== True`

# --- Tests for Stability Poolability (ANCOVA) ---

def test_stability_poolability_when_lots_are_similar():
    """Test the case where lots have similar degradation slopes and should be poolable."""
    # Create two lots with very similar degradation profiles
    lot1 = pd.DataFrame({'lot_id': 'L1', 'timepoint_months': [0, 6, 12], 'purity': [99.5, 99.2, 98.9]})
    lot2 = pd.DataFrame({'lot_id': 'L2', 'timepoint_months': [0, 6, 12], 'purity': [99.4, 99.1, 98.8]})
    test_df = pd.concat([lot1, lot2])
    
    result = analytics.test_stability_poolability(test_df, 'purity')
    assert result['poolable'] is True
    assert result['p_value'] > 0.05

def test_stability_poolability_when_lots_are_different():
    """Test the case where lots have different degradation slopes and should not be pooled."""
    # Create two lots with very different degradation profiles
    lot1 = pd.DataFrame({'lot_id': 'L1', 'timepoint_months': [0, 6, 12], 'purity': [99.5, 99.2, 98.9]}) # Slow degrader
    lot2 = pd.DataFrame({'lot_id': 'L2', 'timepoint_months': [0, 6, 12], 'purity': [99.5, 98.5, 97.5]}) # Fast degrader
    test_df = pd.concat([lot1, lot2])
    
    result = analytics.test_stability_poolability(test_df, 'purity')
    assert result['poolable'] is False
    assert result['p_value'] < 0.05

# --- Tests for Anomaly Detection ---

def test_run_anomaly_detection():
    """Test the Isolation Forest anomaly detection engine."""
    # Create a dataset with a clear outlier
    data = pd.DataFrame({
        'x': [1, 1.1, 0.9, 1.2, 0.8, 10], # 10 is the outlier
        'y': [2, 2.1, 1.9, 2.2, 1.8, 20]  # 20 is the outlier
    })
    
    predictions, fitted_data = analytics.run_anomaly_detection(data, ['x', 'y'], contamination=0.17) # 1/6 = ~0.17
    
    assert len(predictions) == len(data)
    assert predictions[-1] == -1 # The last point should be flagged as an anomaly
    assert np.all(predictions[:-1] == 1) # All other points should be inliers
