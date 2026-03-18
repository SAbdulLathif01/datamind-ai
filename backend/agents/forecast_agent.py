"""
Forecast Agent
Detects time-series columns, forecasts with Prophet, and explains
trends, seasonality, and anomalies using GPT-4o.
"""

import json
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
from openai import OpenAI
from core.config import MODEL
from core.state import AgentState

client = OpenAI()


def _df_from_state(state: AgentState) -> pd.DataFrame:
    data = json.loads(state.cleaned_df_json)
    return pd.DataFrame(data["data"], columns=data["columns"])


def _run_prophet(df: pd.DataFrame, date_col: str, value_col: str, periods: int = 30) -> dict:
    try:
        from prophet import Prophet
        prophet_df = df[[date_col, value_col]].rename(columns={date_col: "ds", value_col: "y"})
        prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])
        prophet_df = prophet_df.dropna().sort_values("ds")

        model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
        model.fit(prophet_df)

        future = model.make_future_dataframe(periods=periods)
        forecast = model.predict(future)

        # Build Plotly chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=prophet_df["ds"], y=prophet_df["y"],
                                  mode="lines", name="Actual",
                                  line=dict(color="#6366f1")))
        fig.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat"],
                                  mode="lines", name="Forecast",
                                  line=dict(color="#f59e0b", dash="dash")))
        fig.add_trace(go.Scatter(
            x=pd.concat([forecast["ds"], forecast["ds"][::-1]]),
            y=pd.concat([forecast["yhat_upper"], forecast["yhat_lower"][::-1]]),
            fill="toself", fillcolor="rgba(245,158,11,0.15)",
            line=dict(color="rgba(255,255,255,0)"), name="Confidence Interval"
        ))
        fig.update_layout(title=f"Forecast: {value_col}", template="plotly_dark",
                           xaxis_title="Date", yaxis_title=value_col)

        # Trend summary
        trend_start = float(forecast["trend"].iloc[0])
        trend_end = float(forecast["trend"].iloc[-1])
        trend_dir = "upward" if trend_end > trend_start else "downward"

        return {
            "date_col": date_col,
            "value_col": value_col,
            "periods_forecast": periods,
            "trend_direction": trend_dir,
            "forecast_chart": json.loads(fig.to_json()),
            "last_actual": float(prophet_df["y"].iloc[-1]),
            "forecast_30d": float(forecast["yhat"].iloc[-1]),
            "forecast_min": float(forecast["yhat_lower"].iloc[-1]),
            "forecast_max": float(forecast["yhat_upper"].iloc[-1]),
            "components": {
                "trend": forecast[["ds", "trend"]].tail(30).to_dict(orient="records"),
                "weekly": forecast[["ds", "weekly"]].tail(7).to_dict(orient="records") if "weekly" in forecast else []
            }
        }
    except ImportError:
        return {"error": "Prophet not installed. Run: pip install prophet"}
    except Exception as e:
        return {"error": str(e)}


def _ai_forecast_insights(forecast_data: dict) -> str:
    prompt = f"""You are a time series analyst. Interpret these forecast results:

{json.dumps({k: v for k, v in forecast_data.items() if k not in ['forecast_chart', 'components']}, indent=2)}

Provide:
1. **Trend Analysis** — what direction is the metric heading?
2. **Key Forecast Insight** — what should stakeholders know?
3. **Risk Factors** — confidence interval width and uncertainty
4. **Recommended Actions** — based on the forecast
"""
    response = client.chat.completions.create(
        model=MODEL, max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def run_forecast_agent(state: AgentState) -> AgentState:
    log = []
    log.append({"agent": "ForecastAgent", "message": "Checking for time series...",
                 "timestamp": datetime.now().isoformat(), "status": "running"})
    try:
        df = _df_from_state(state)

        # Find datetime columns
        dt_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
        if not dt_cols:
            state.forecast_results = {"skipped": True, "reason": "No datetime columns detected"}
            state.completed_agents.append("forecast")
            log.append({"agent": "ForecastAgent",
                         "message": "⏭️ Skipped — no datetime columns",
                         "timestamp": datetime.now().isoformat(), "status": "done"})
            state.activity_log.extend(log)
            return state

        date_col = dt_cols[0]
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not num_cols:
            raise ValueError("No numeric columns to forecast")

        value_col = num_cols[0]
        log.append({"agent": "ForecastAgent",
                     "message": f"Forecasting '{value_col}' over '{date_col}'...",
                     "timestamp": datetime.now().isoformat(), "status": "running"})

        forecast_data = _run_prophet(df, date_col, value_col)

        if "error" not in forecast_data:
            insights = _ai_forecast_insights(forecast_data)
            forecast_data["ai_insights"] = insights

        state.forecast_results = forecast_data
        state.completed_agents.append("forecast")
        log.append({"agent": "ForecastAgent", "message": "✅ Forecast complete",
                     "timestamp": datetime.now().isoformat(), "status": "done"})

    except Exception as e:
        state.forecast_results = {"error": str(e)}
        log.append({"agent": "ForecastAgent", "message": f"❌ Error: {e}",
                     "timestamp": datetime.now().isoformat(), "status": "error"})

    state.activity_log.extend(log)
    return state
