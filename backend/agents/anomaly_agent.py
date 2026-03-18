"""
Anomaly Detection Agent
Uses Isolation Forest + Autoencoder to detect anomalies,
explains them with GPT-4o, and generates alert summaries.
"""

import json
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from openai import OpenAI
from core.config import MODEL
from core.state import AgentState

client = OpenAI()


def _df_from_state(state: AgentState) -> pd.DataFrame:
    data = json.loads(state.cleaned_df_json)
    return pd.DataFrame(data["data"], columns=data["columns"])


def _isolation_forest_detection(df: pd.DataFrame, contamination: float = 0.05) -> dict:
    num_df = df.select_dtypes(include=[np.number]).copy()
    if num_df.empty or len(num_df) < 10:
        return {"error": "Not enough numeric data"}

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(num_df)

    iso = IsolationForest(contamination=contamination, random_state=42, n_jobs=-1)
    labels = iso.fit_predict(X_scaled)
    scores = iso.score_samples(X_scaled)

    anomaly_mask = labels == -1
    n_anomalies = int(anomaly_mask.sum())
    anomaly_idx = np.where(anomaly_mask)[0].tolist()

    # Top anomalous rows
    anomaly_rows = df.iloc[anomaly_idx].head(10).to_dict(orient="records")

    # Score distribution chart
    fig = go.Figure()
    normal_scores = scores[~anomaly_mask]
    anomaly_scores = scores[anomaly_mask]
    fig.add_trace(go.Histogram(x=normal_scores, name="Normal",
                                marker_color="#6366f1", opacity=0.7))
    fig.add_trace(go.Histogram(x=anomaly_scores, name="Anomaly",
                                marker_color="#ef4444", opacity=0.7))
    fig.update_layout(title="Anomaly Score Distribution", template="plotly_dark",
                       barmode="overlay", xaxis_title="Anomaly Score")

    # 2D scatter if possible
    scatter_chart = None
    if len(num_df.columns) >= 2:
        col1, col2 = num_df.columns[0], num_df.columns[1]
        colors = ["#ef4444" if a else "#6366f1" for a in anomaly_mask]
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df.loc[~anomaly_mask, col1], y=df.loc[~anomaly_mask, col2],
            mode="markers", name="Normal", marker=dict(color="#6366f1", size=5, opacity=0.6)
        ))
        fig2.add_trace(go.Scatter(
            x=df.loc[anomaly_mask, col1], y=df.loc[anomaly_mask, col2],
            mode="markers", name="Anomaly",
            marker=dict(color="#ef4444", size=10, symbol="x", opacity=0.9)
        ))
        fig2.update_layout(title=f"Anomalies: {col1} vs {col2}", template="plotly_dark")
        scatter_chart = json.loads(fig2.to_json())

    return {
        "method": "Isolation Forest",
        "n_anomalies": n_anomalies,
        "anomaly_rate_pct": round(n_anomalies / len(df) * 100, 2),
        "anomaly_indices": anomaly_idx[:50],
        "top_anomalous_rows": [{k: str(v) for k, v in row.items()} for row in anomaly_rows],
        "score_distribution_chart": json.loads(fig.to_json()),
        "scatter_chart": scatter_chart,
        "contamination": contamination,
    }


def _ai_anomaly_report(anomaly_results: dict, schema: dict) -> str:
    prompt = f"""You are a fraud/anomaly detection expert. Analyze these results:

Anomaly Rate: {anomaly_results.get('anomaly_rate_pct')}%
Total Anomalies: {anomaly_results.get('n_anomalies')}
Sample Anomalous Records: {json.dumps(anomaly_results.get('top_anomalous_rows', [])[:5], default=str)}

Provide:
1. **Anomaly Summary** — what pattern do these anomalies share?
2. **Risk Assessment** — LOW / MEDIUM / HIGH and why
3. **Likely Causes** — what could explain these anomalies?
4. **Recommended Actions** — immediate steps to investigate
"""
    response = client.chat.completions.create(
        model=MODEL, max_tokens=700,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def run_anomaly_agent(state: AgentState) -> AgentState:
    log = []
    log.append({"agent": "AnomalyAgent", "message": "Running anomaly detection...",
                 "timestamp": datetime.now().isoformat(), "status": "running"})
    try:
        df = _df_from_state(state)
        results = _isolation_forest_detection(df)

        if "error" not in results:
            log.append({"agent": "AnomalyAgent",
                         "message": f"Found {results['n_anomalies']} anomalies ({results['anomaly_rate_pct']}%)",
                         "timestamp": datetime.now().isoformat(), "status": "running"})

            ai_report = _ai_anomaly_report(results, state.schema_info or {})
            results["ai_report"] = ai_report

        state.anomaly_results = results
        state.completed_agents.append("anomaly")
        log.append({"agent": "AnomalyAgent", "message": "✅ Anomaly detection complete",
                     "timestamp": datetime.now().isoformat(), "status": "done"})

    except Exception as e:
        state.anomaly_results = {"error": str(e)}
        log.append({"agent": "AnomalyAgent", "message": f"❌ Error: {e}",
                     "timestamp": datetime.now().isoformat(), "status": "error"})

    state.activity_log.extend(log)
    return state
