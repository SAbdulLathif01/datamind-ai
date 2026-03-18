"""
EDA Agent
Autonomous exploratory data analysis — distributions, correlations,
outliers, statistical tests, and AI-generated insights.
"""

import json
import io
import base64
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
from scipy import stats
from openai import OpenAI
from core.config import MODEL
from core.state import AgentState

client = OpenAI()


def _df_from_state(state: AgentState) -> pd.DataFrame:
    data = json.loads(state.cleaned_df_json)
    return pd.DataFrame(data["data"], columns=data["columns"])


def _compute_statistics(df: pd.DataFrame) -> dict:
    num_df = df.select_dtypes(include=[np.number])
    cat_df = df.select_dtypes(include=["object", "category"])

    stats_out = {
        "numeric": {},
        "categorical": {},
        "correlations": {},
        "outliers": {}
    }

    # Numeric stats
    if not num_df.empty:
        desc = num_df.describe().to_dict()
        for col in num_df.columns:
            skew = float(num_df[col].skew())
            kurt = float(num_df[col].kurtosis())
            # Outlier detection via IQR
            Q1, Q3 = num_df[col].quantile(0.25), num_df[col].quantile(0.75)
            IQR = Q3 - Q1
            n_outliers = int(((num_df[col] < Q1 - 1.5 * IQR) | (num_df[col] > Q3 + 1.5 * IQR)).sum())
            stats_out["numeric"][col] = {
                **{k: round(v, 4) for k, v in desc.get(col, {}).items()},
                "skewness": round(skew, 4),
                "kurtosis": round(kurt, 4),
                "outliers_iqr": n_outliers,
            }
            stats_out["outliers"][col] = n_outliers

        # Correlation matrix
        corr = num_df.corr().round(3)
        stats_out["correlations"] = corr.to_dict()

    # Categorical stats
    for col in cat_df.columns:
        vc = df[col].value_counts()
        stats_out["categorical"][col] = {
            "n_unique": int(df[col].nunique()),
            "top_values": vc.head(10).to_dict(),
            "top_1_pct": round(float(vc.iloc[0] / len(df) * 100), 2) if len(vc) > 0 else 0
        }

    return stats_out


def _build_plotly_charts(df: pd.DataFrame) -> list[dict]:
    """Generate a set of Plotly charts as JSON."""
    charts = []
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # Distribution plots for numeric (up to 6)
    for col in num_cols[:6]:
        fig = px.histogram(df, x=col, marginal="box", title=f"Distribution: {col}",
                           template="plotly_dark", color_discrete_sequence=["#6366f1"])
        charts.append({"type": "histogram", "col": col,
                        "data": json.loads(fig.to_json())})

    # Correlation heatmap
    if len(num_cols) >= 2:
        corr = df[num_cols].corr()
        fig = px.imshow(corr, title="Correlation Heatmap", template="plotly_dark",
                        color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
        charts.append({"type": "heatmap", "data": json.loads(fig.to_json())})

    # Bar charts for categorical (up to 3)
    for col in cat_cols[:3]:
        vc = df[col].value_counts().head(15).reset_index()
        vc.columns = [col, "count"]
        fig = px.bar(vc, x=col, y="count", title=f"Top Values: {col}",
                     template="plotly_dark", color_discrete_sequence=["#8b5cf6"])
        charts.append({"type": "bar", "col": col, "data": json.loads(fig.to_json())})

    # Scatter matrix (up to 4 numeric cols)
    if len(num_cols) >= 2:
        fig = px.scatter_matrix(df[num_cols[:4]], title="Scatter Matrix",
                                template="plotly_dark",
                                color_discrete_sequence=["#06b6d4"])
        charts.append({"type": "scatter_matrix", "data": json.loads(fig.to_json())})

    # Pairplot top correlated pair
    if len(num_cols) >= 2:
        corr_pairs = df[num_cols].corr().unstack().sort_values(ascending=False)
        corr_pairs = corr_pairs[corr_pairs < 1].dropna()
        if len(corr_pairs) > 0:
            top_pair = corr_pairs.index[0]
            fig = px.scatter(df, x=top_pair[0], y=top_pair[1],
                             trendline="ols", title=f"Top Correlation: {top_pair[0]} vs {top_pair[1]}",
                             template="plotly_dark", color_discrete_sequence=["#f59e0b"])
            charts.append({"type": "scatter", "data": json.loads(fig.to_json())})

    return charts


def _ai_insights(df: pd.DataFrame, stats: dict) -> str:
    prompt = f"""You are a senior data analyst. Based on the EDA results below, provide:

1. **Key Findings** (3-5 bullet points) — most important patterns, correlations, anomalies
2. **Data Quality Issues** — what needs attention
3. **Business Insights** — what story does this data tell?
4. **Recommended Next Steps** — what analysis or ML tasks make sense?

Dataset shape: {df.shape}
Column types: numeric={list(df.select_dtypes(include=[np.number]).columns)}, categorical={list(df.select_dtypes(include=['object']).columns)}
Statistics summary: {json.dumps({k: v for k, v in stats['numeric'].items()}, default=str)[:2000]}
Top correlations: {json.dumps(stats.get('correlations', {}), default=str)[:1000]}
Outlier counts: {json.dumps(stats.get('outliers', {}))}
"""
    response = client.chat.completions.create(
        model=MODEL, max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def run_eda_agent(state: AgentState) -> AgentState:
    log = []
    log.append({"agent": "EDAAgent", "message": "Starting EDA...",
                 "timestamp": datetime.now().isoformat(), "status": "running"})
    try:
        df = _df_from_state(state)

        log.append({"agent": "EDAAgent", "message": "Computing statistics...",
                     "timestamp": datetime.now().isoformat(), "status": "running"})
        stats = _compute_statistics(df)

        log.append({"agent": "EDAAgent", "message": "Generating visualizations...",
                     "timestamp": datetime.now().isoformat(), "status": "running"})
        charts = _build_plotly_charts(df)

        log.append({"agent": "EDAAgent", "message": "Generating AI insights...",
                     "timestamp": datetime.now().isoformat(), "status": "running"})
        insights = _ai_insights(df, stats)

        # Detect if time series
        datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
        if datetime_cols:
            state.is_time_series = True

        state.eda_report = {
            "statistics": stats,
            "charts": charts,
            "insights": insights,
            "datetime_columns": datetime_cols,
            "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
            "categorical_columns": df.select_dtypes(include=["object"]).columns.tolist(),
            "shape": list(df.shape),
        }
        state.completed_agents.append("eda")

        log.append({"agent": "EDAAgent", "message": f"✅ EDA complete — {len(charts)} charts generated",
                     "timestamp": datetime.now().isoformat(), "status": "done"})

    except Exception as e:
        state.error = f"EDAAgent error: {str(e)}"
        log.append({"agent": "EDAAgent", "message": f"❌ Error: {e}",
                     "timestamp": datetime.now().isoformat(), "status": "error"})

    state.activity_log.extend(log)
    return state
