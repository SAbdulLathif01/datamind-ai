from typing import Any, Optional
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    """Shared state passed between all agents in the LangGraph pipeline."""

    # Input
    session_id: str
    file_path: Optional[str] = None
    user_query: Optional[str] = None

    # Data
    raw_df_json: Optional[str] = None          # JSON-serialized DataFrame
    cleaned_df_json: Optional[str] = None
    schema_info: Optional[dict] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None

    # EDA results
    eda_report: Optional[dict] = None

    # ML results
    ml_results: Optional[dict] = None
    best_model_name: Optional[str] = None
    feature_importance: Optional[dict] = None

    # Forecast results
    forecast_results: Optional[dict] = None
    is_time_series: bool = False

    # Anomaly results
    anomaly_results: Optional[dict] = None

    # Chat / NL→SQL
    sql_query: Optional[str] = None
    query_result: Optional[str] = None
    chat_history: list[dict] = Field(default_factory=list)

    # Agent activity log (streamed to frontend)
    activity_log: list[dict] = Field(default_factory=list)

    # Final report
    report_path: Optional[str] = None
    error: Optional[str] = None

    # Control
    next_agent: Optional[str] = None
    completed_agents: list[str] = Field(default_factory=list)
