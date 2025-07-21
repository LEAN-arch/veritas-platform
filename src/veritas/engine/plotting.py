# src/veritas/engine/plotting.py

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats
import graphviz
from typing import Dict, List, Optional, Any

# Import the centralized settings for colors and configurations
from .. import config

# --- Universal Helper ---

def create_empty_figure(message: str) -> go.Figure:
    """
    Creates a standardized empty Plotly figure with a text message.
    This is used as a fallback when a plot cannot be generated due to missing data or errors.

    Args:
        message (str): The message to display on the empty figure.

    Returns:
        go.Figure: An empty Plotly figure object with a centered annotation.
    """
    fig = go.Figure()
    fig.update_layout(
        xaxis={'visible': False},
        yaxis={'visible': False},
        annotations=[{
            'text': message,
            'xref': 'paper',
            'yref': 'paper',
            'showarrow': False,
            'font': {'size': 16, 'color': 'grey'}
        }]
    )
    return fig

# --- Homepage & Strategic Plots ---

def plot_program_risk_matrix(df: pd.DataFrame) -> go.Figure:
    """
    Creates a 2x2 risk matrix bubble chart for monitoring program-level risks.

    Args:
        df (pd.DataFrame): DataFrame must contain 'program_id', 'days_to_milestone',
                           'dqs', 'active_deviations', and 'risk_quadrant'.

    Returns:
        go.Figure: A Plotly scatter plot figure object.
    """
    required_cols = ['program_id', 'days_to_milestone', 'dqs', 'active_deviations', 'risk_quadrant']
    if not all(col in df.columns for col in required_cols):
        return create_empty_figure(f"Risk matrix data is missing required columns.")

    if df.empty:
        return create_empty_figure("No program risk data available to display.")

    color_map = {
        "On Track": config.config.COLORS.green,
        "Data Risk": config.config.COLORS.orange,
        "Schedule Risk": config.config.COLORS.lightblue,
        "High Priority": config.config.COLORS.red
    }
    
    fig = px.scatter(
        df,
        x="days_to_milestone",
        y="dqs",
        size="active_deviations",
        color="risk_quadrant",
        text="program_id",
        hover_name="program_id",
        hover_data={
            "days_to_milestone": True, "dqs": ':.1f',
            "active_deviations": True, "risk_quadrant": False
        },
        color_discrete_map=color_map,
        size_max=60,
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(
        xaxis_title="Days to Next Milestone",
        yaxis_title="Data Quality Score (%)",
        xaxis=dict(autorange="reversed"),
        legend_title="Risk Quadrant"
    )
    return fig

def plot_pareto_chart(df: pd.DataFrame, category_col: str, value_col: str) -> go.Figure:
    """
    Creates a Pareto chart from a frequency DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing the data.
        category_col (str): The column with the categories (e.g., 'Error Type').
        value_col (str): The numeric column with frequencies (e.g., 'Frequency').

    Returns:
        go.Figure: A Plotly figure object representing the Pareto chart.
    """
    required_cols = [category_col, value_col]
    if not all(col in df.columns for col in required_cols):
        return create_empty_figure(f"Pareto chart data is missing required columns.")

    if df.empty or df[value_col].sum() == 0:
        return create_empty_figure("No data available for Pareto analysis.")

    df_sorted = df.sort_values(by=value_col, ascending=False).copy()
    total_freq = df_sorted[value_col].sum()
    df_sorted['cumulative_percentage'] = df_sorted[value_col].cumsum() / total_freq * 100

    fig = go.Figure()
    # Bar chart for individual frequencies
    fig.add_trace(go.Bar(
        x=df_sorted[category_col], y=df_sorted[value_col],
        name='Count', marker_color=config.config.COLORS.orange
    ))
    # Line chart for cumulative percentage
    fig.add_trace(go.Scatter(
        x=df_sorted[category_col], y=df_sorted['cumulative_percentage'],
        name='Cumulative %', yaxis='y2', # Link to the secondary y-axis
        mode='lines+markers', line=dict(color=config.config.COLORS.blue)
    ))
    
    fig.update_layout(
        yaxis_title='Frequency Count',
        yaxis2=dict(
            title='Cumulative Percentage (%)', overlaying='y', side='right',
            range=[0, 105], showgrid=False
        ),
        legend=dict(x=0.01, y=0.99, xanchor='left', yanchor='top')
    )
    return fig

# --- Statistical & QC Plots ---

def plot_historical_control_chart(df: pd.DataFrame, cqa: str, events_df: Optional[pd.DataFrame] = None) -> go.Figure:
    """
    Creates a historical Individual (I) Chart with an optional overlay of deviation events.

    Args:
        df (pd.DataFrame): DataFrame with 'injection_time' and the specified cqa column.
        cqa (str): The Critical Quality Attribute column to plot.
        events_df (Optional[pd.DataFrame]): Optional DataFrame of events to overlay.

    Returns:
        go.Figure: A Plotly figure object representing the control chart.
    """
    required_cols = ['injection_time', cqa]
    if not all(col in df.columns for col in required_cols):
        return create_empty_figure(f"Control chart data is missing required columns.")
    if len(df[cqa].dropna()) < 2:
        return create_empty_figure(f"Not enough data to plot control chart for {cqa}.")
    
    data = df.sort_values(by='injection_time')
    mean = data[cqa].mean()
    std_dev = data[cqa].std()
    ucl, lcl = mean + 3 * std_dev, mean - 3 * std_dev

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['injection_time'], y=data[cqa], mode='lines+markers', name=cqa))
    fig.add_hline(y=mean, line_dash="dash", line_color=config.config.COLORS.green, annotation_text="Mean")
    fig.add_hline(y=ucl, line_dash="dot", line_color=config.config.COLORS.red, annotation_text="UCL (3σ)")
    fig.add_hline(y=lcl, line_dash="dot", line_color=config.config.COLORS.red, annotation_text="LCL (3σ)")
    
    if events_df is not None and not events_df.empty and pd.api.types.is_datetime64_any_dtype(events_df.get('timestamp')):
        for _, event in events_df.iterrows():
            fig.add_vline(
                x=event['timestamp'], line_dash="longdash",
                line_color=config.config.COLORS.gray, annotation_text=f"Event: {event['id']}"
            )

    fig.update_layout(xaxis_title="Date", yaxis_title="Value", showlegend=False)
    return fig

def plot_process_capability(df: pd.DataFrame, cqa: str, lsl: Optional[float], usl: Optional[float], cpk: float, cpk_target: float) -> go.Figure:
    """
    Creates a process capability histogram with overlaid specification limits and a dynamic title.

    Args:
        df (pd.DataFrame): DataFrame containing the CQA data.
        cqa (str): The CQA column to plot.
        lsl (Optional[float]): Lower specification limit.
        usl (Optional[float]): Upper specification limit.
        cpk (float): Calculated Process Capability Index.
        cpk_target (float): The target Cpk value for visual comparison.

    Returns:
        go.Figure: A Plotly histogram figure object.
    """
    if df[cqa].dropna().empty:
        return create_empty_figure(f"No data to plot process capability for {cqa}.")

    title_color = config.config.COLORS.green if cpk >= cpk_target else config.config.COLORS.red
    fig = px.histogram(df, x=cqa, nbins=40, title=f"<b>Cpk: {cpk:.2f}</b>")
    
    if lsl is not None:
        fig.add_vline(x=lsl, line_dash="solid", line_color=config.config.COLORS.red, annotation_text="LSL")
    if usl is not None:
        fig.add_vline(x=usl, line_dash="solid", line_color=config.config.COLORS.red, annotation_text="USL")
    fig.add_vline(x=df[cqa].mean(), line_dash="dash", line_color=config.config.COLORS.green, annotation_text="Mean")
    
    fig.update_layout(title_font_color=title_color)
    return fig

def plot_stability_trend(df: pd.DataFrame, assay: str, title: str, spec_limits: Any, projection: Optional[Dict]) -> go.Figure:
    """
    Creates a stability trend scatter plot with an optional regression line.

    Args:
        df (pd.DataFrame): Stability data with 'lot_id', 'timepoint_months', and assay columns.
        assay (str): The assay column to plot.
        title (str): The title for the plot.
        spec_limits (Any): A config object with 'lsl' and 'usl' attributes.
        projection (Optional[Dict]): A dictionary with regression results from `calculate_stability_projection`.

    Returns:
        go.Figure: A Plotly scatter plot figure object.
    """
    required_cols = ['lot_id', 'timepoint_months', assay]
    if not all(col in df.columns for col in required_cols):
        return create_empty_figure(f"Stability trend data is missing required columns.")

    fig = px.scatter(df, x='timepoint_months', y=assay, color='lot_id', title=f"<b>{title}</b>")

    if projection and 'pred_x' in projection:
        fig.add_trace(go.Scatter(
            x=projection['pred_x'], y=projection['pred_y'], mode='lines',
            name='Regression Fit', line=dict(color=config.config.COLORS.gray, dash='dash')
        ))

    if spec_limits and spec_limits.lsl is not None:
        fig.add_hline(y=spec_limits.lsl, line_dash="solid", line_color=config.config.COLORS.red, annotation_text="LSL")
    if spec_limits and spec_limits.usl is not None:
        fig.add_hline(y=spec_limits.usl, line_dash="solid", line_color=config.config.COLORS.red, annotation_text="USL")
    
    fig.update_layout(xaxis_title="Timepoint (Months)", yaxis_title="Value")
    return fig

def plot_anova_results(df: pd.DataFrame, value_col: str, group_col: str, anova_results: Dict) -> go.Figure:
    """
    Creates a box plot for ANOVA results with a p-value in the title.

    Args:
        df (pd.DataFrame): DataFrame containing the data.
        value_col (str): The numeric column to test.
        group_col (str): The categorical column to group by.
        anova_results (Dict): The results dictionary from `perform_anova`.

    Returns:
        go.Figure: A Plotly box plot figure object.
    """
    p_value = anova_results.get('p_value')
    if p_value is None:
        return create_empty_figure("ANOVA test failed; cannot generate plot.")

    title_text = f"<b>Distribution by {group_col} (p-value: {p_value:.4f})</b>"
    fig = px.box(df, x=group_col, y=value_col, points="all", color=group_col, title=title_text)
    return fig

def plot_qq(data: pd.Series) -> go.Figure:
    """
    Generates a Quantile-Quantile (Q-Q) plot to assess normality.

    Args:
        data (pd.Series): The data series to plot.

    Returns:
        go.Figure: A Plotly Q-Q plot figure object.
    """
    data_clean = data.dropna()
    if len(data_clean) < 3:
        return create_empty_figure("Not enough data points for Q-Q plot.")

    qq_data = stats.probplot(data_clean, dist="norm")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=qq_data[0][0], y=qq_data[0][1], mode='markers', name='Data Points'))
    fig.add_trace(go.Scatter(
        x=qq_data[0][0], y=qq_data[1][1] + qq_data[1][0] * qq_data[0][0],
        mode='lines', name='Normal Fit', line=dict(color=config.config.COLORS.red)
    ))
    
    fig.update_layout(xaxis_title="Theoretical Quantiles", yaxis_title="Sample Quantiles", showlegend=False)
    return fig

def plot_ml_anomaly_results_3d(df: pd.DataFrame, cols: List[str], labels: np.ndarray) -> go.Figure:
    """
    Creates a 3D scatter plot of anomaly detection results.

    Args:
        df (pd.DataFrame): DataFrame containing the feature columns.
        cols (List[str]): Exactly three column names for the x, y, and z axes.
        labels (np.ndarray): An array of labels (-1 for anomalies, 1 for inliers).

    Returns:
        go.Figure: A Plotly 3D scatter plot figure object.
    """
    if len(cols) != 3:
        raise ValueError("This 3D plot requires exactly three columns.")
    if len(labels) != len(df):
        raise ValueError("Length of labels must match the length of the DataFrame.")

    df_plot = df.copy()
    df_plot['Anomaly'] = labels
    df_plot['Anomaly'] = df_plot['Anomaly'].astype(str).replace({'1': 'Normal', '-1': 'Anomaly'})
    
    fig = px.scatter_3d(
        df_plot, x=cols[0], y=cols[1], z=cols[2], color='Anomaly',
        color_discrete_map={'Normal': config.config.COLORS.blue, 'Anomaly': config.config.COLORS.red},
        title=f"<b>Isolation Forest Anomaly Detection</b>",
        hover_data=df.columns
    )
    return fig

# --- Governance & Audit Plots ---

def plot_data_lineage_graph(df: pd.DataFrame, record_id: str) -> graphviz.Digraph:
    """
    Creates a Graphviz Digraph object for visualizing data lineage.

    Args:
        df (pd.DataFrame): The audit log DataFrame.
        record_id (str): The specific record ID to trace.

    Returns:
        graphviz.Digraph: A Graphviz Digraph object ready for rendering.
    """
    required_cols = ['record_id', 'timestamp', 'user', 'action']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Lineage DataFrame is missing required columns.")

    dot = graphviz.Digraph(comment=f'Lineage for {record_id}')
    dot.attr(rankdir='TB', splines='ortho')
    dot.attr('node', shape='box', style='rounded,filled', fillcolor=config.config.COLORS.lightcyan, fontname="Helvetica")
    dot.attr('edge', fontname="Helvetica")

    record_df = df[df['record_id'] == record_id].sort_values('timestamp').copy()
    if record_df.empty:
        dot.node('empty', f'No lineage data found for Record ID:\n{record_id}')
        return dot

    for i, (_, row) in enumerate(record_df.iterrows()):
        node_id = f'event_{i}'
        # Use HTML-like labels for better formatting and control
        label = f"<{row['action']}<br/><font point-size='10'>By: {row['user']}</font><br/><font point-size='9'>{row['timestamp'].strftime('%Y-%m-%d %H:%M')}</font>>"
        dot.node(node_id, label)
        if i > 0:
            dot.edge(f'event_{i-1}', node_id)
            
    return dot
