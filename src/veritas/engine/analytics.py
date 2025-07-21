# /mount/src/verita/veritas_core/engine/analytics.py

import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from sklearn.ensemble import IsolationForest
from typing import Dict, List, Tuple, Optional, Any  # <-- DEFINITIVE FIX IS HERE

# --- Statistical Process Control (SPC) ---

def calculate_cpk(data_series: pd.Series, lsl: Optional[float], usl: Optional[float]) -> float:
    """
    Calculate the Process Capability Index (Cpk), robustly handling single-sided specifications.
    """
    if not isinstance(data_series, pd.Series):
        raise TypeError("data_series must be a pandas Series.")

    data_clean = data_series.dropna()
    if len(data_clean) < 2:
        return 0.0
        
    std_dev = data_clean.std()
    if std_dev == 0:
        return 0.0

    mean = data_clean.mean()
    
    if usl is None and lsl is None:
        return np.inf

    cpu = (usl - mean) / (3 * std_dev) if usl is not None else np.inf
    cpl = (mean - lsl) / (3 * std_dev) if lsl is not None else np.inf
    
    return min(cpu, cpl)

# --- Stability Analysis ---

def test_stability_poolability(df: pd.DataFrame, assay: str, time_col: str = 'timepoint_months', group_col: str = 'lot_id') -> Dict:
    """
    Perform an ANCOVA test to determine if stability data from multiple lots can be pooled.
    """
    required_cols = [group_col, time_col, assay]
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")

    df_clean = df[required_cols].dropna()
    if df_clean[group_col].nunique() < 2 or len(df_clean) < 4:
        return {'poolable': True, 'p_value': 1.0, 'reason': 'Insufficient data for test.'}

    try:
        formula = f"`{assay}` ~ `{time_col}` * C(`{group_col}`)"
        model = ols(formula, data=df_clean).fit()
        anova_table = anova_lm(model, typ=2)

        interaction_term_name = f"`{time_col}`:C(`{group_col}`)"
        interaction_p_value = anova_table["PR(>F)"][interaction_term_name]

        poolable = interaction_p_value > 0.05
        reason = "Slopes are not significantly different." if poolable else "Slopes are significantly different."
        
        return {'poolable': poolable, 'p_value': interaction_p_value, 'reason': reason}
    except Exception as e:
        return {'poolable': False, 'p_value': 0.0, 'reason': f'ANCOVA test failed: {e}'}

def calculate_stability_projection(df: pd.DataFrame, assay: str, use_pooled_data: bool) -> Dict:
    """
    Perform linear regression on stability data to project trends.
    """
    required_cols = ['lot_id', 'timepoint_months', assay]
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")

    df_clean = df[required_cols].dropna()
    if len(df_clean) < 2: return {}

    target_df = df_clean if use_pooled_data else df_clean[df_clean['lot_id'] == df_clean['lot_id'].unique()[0]]
    if len(target_df) < 2: return {}

    try:
        slope, intercept, r_value, p_value, std_err = stats.linregress(target_df['timepoint_months'], target_df[assay])
        pred_x = np.array([target_df['timepoint_months'].min(), target_df['timepoint_months'].max()])
        pred_y = intercept + slope * pred_x
        return {
            'slope': slope, 'intercept': intercept, 'r_squared': r_value**2,
            'p_value': p_value, 'std_err': std_err, 'pred_x': pred_x, 'pred_y': pred_y
        }
    except Exception:
        return {}

# --- Rule-Based QC Engine ---

def apply_qc_rules(df: pd.DataFrame, rules_config: dict, app_config: Any) -> pd.DataFrame:
    """
    Apply deterministic QC rules to a dataframe and return a report of discrepancies.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")
    if 'sample_id' not in df.columns:
        raise ValueError("DataFrame must contain 'sample_id' column.")

    discrepancies = []
    
    if rules_config.get('check_nulls'):
        key_cols = [col for col in app_config.process_capability.available_cqas if col in df.columns]
        null_rows = df[df[key_cols].isnull().any(axis=1)]
        for _, row in null_rows.iterrows():
            null_cols = row[key_cols].index[row[key_cols].isnull()].tolist()
            discrepancies.append({'sample_id': row['sample_id'], 'Issue': 'Missing Value', 'Details': f"Null in critical column(s): {', '.join(null_cols)}"})
    
    if rules_config.get('check_negatives') and 'bio_activity' in df.columns:
        negative_rows = df[df['bio_activity'] < 0]
        for _, row in negative_rows.iterrows():
            discrepancies.append({'sample_id': row['sample_id'], 'Issue': 'Impossible Negative Value', 'Details': f"bio_activity is {row['bio_activity']:.2f}, which is impossible."})

    if rules_config.get('check_spec_limits'):
        for cqa, specs in app_config.process_capability.spec_limits.items():
            if cqa in df.columns:
                oor_mask = (df[cqa] < specs.lsl if specs.lsl is not None else False) | (df[cqa] > specs.usl if specs.usl is not None else False)
                for _, row in df[oor_mask & df[cqa].notna()].iterrows():
                    discrepancies.append({'sample_id': row['sample_id'], 'Issue': 'Out of Specification', 'Details': f"CQA '{cqa}' value of {row[cqa]:.2f} is outside spec limits (LSL: {specs.lsl}, USL: {specs.usl})."})

    return pd.DataFrame(discrepancies) if discrepancies else pd.DataFrame()

# --- Advanced Statistical Analysis ---

def perform_normality_test(data_series: pd.Series) -> Dict:
    """Perform a Shapiro-Wilk test for normality."""
    data_clean = data_series.dropna()
    if len(data_clean) < 3:
        return {'conclusion': 'Insufficient data (need >= 3).'}
    stat, p_value = stats.shapiro(data_clean)
    conclusion = "Data appears normal (p > 0.05)." if p_value > 0.05 else "Data is likely non-normal (p <= 0.05)."
    return {'statistic': stat, 'p_value': p_value, 'conclusion': conclusion}

def perform_anova(df: pd.DataFrame, value_col: str, group_col: str) -> Dict:
    """Perform a one-way Analysis of Variance (ANOVA) test."""
    df_clean = df[[value_col, group_col]].dropna()
    groups = [group_data[value_col] for _, group_data in df_clean.groupby(group_col)]
    if len(groups) < 2:
        return {'reason': 'Insufficient data (need at least 2 groups).'}
    f_stat, p_value = stats.f_oneway(*groups)
    return {'f_statistic': f_stat, 'p_value': p_value}

def perform_tukey_hsd(df: pd.DataFrame, value_col: str, group_col: str) -> pd.DataFrame:
    """Perform a Tukey's Honestly Significant Difference (HSD) post-hoc test."""
    df_clean = df[[value_col, group_col]].dropna()
    if df_clean[group_col].nunique() < 2:
        return pd.DataFrame()
    tukey_result = pairwise_tukeyhsd(endog=df_clean[value_col], groups=df_clean[group_col], alpha=0.05)
    return pd.DataFrame(data=tukey_result._results_table.data[1:], columns=tukey_result._results_table.data[0])

# --- Machine Learning Engine ---

def run_anomaly_detection(df: pd.DataFrame, cols: List[str], contamination: float, random_state: int = 42) -> Tuple[np.ndarray, pd.DataFrame]:
    """Run the Isolation Forest model for anomaly detection."""
    if not all(c in df.columns for c in cols):
        raise ValueError(f"DataFrame must contain all specified columns: {cols}")
    if not 0 < contamination < 0.5:
        raise ValueError("Contamination must be between 0 and 0.5.")

    data_to_fit = df[cols].dropna()
    if len(data_to_fit) < 2:
        return np.array([]), pd.DataFrame(columns=cols)

    model = IsolationForest(contamination=contamination, random_state=random_state)
    predictions = model.fit_predict(data_to_fit)
    return predictions, data_to_fit
