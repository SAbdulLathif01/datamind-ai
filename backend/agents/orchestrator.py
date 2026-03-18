"""
Orchestrator Agent — LangGraph StateMachine
Routes between all agents based on data characteristics and user intent.
"""

from langgraph.graph import StateGraph, END
from core.state import AgentState
from agents.ingest_agent import run_ingest_agent
from agents.eda_agent import run_eda_agent
from agents.ml_agent import run_ml_agent
from agents.forecast_agent import run_forecast_agent
from agents.anomaly_agent import run_anomaly_agent
from agents.chat_agent import run_chat_agent


def _should_run_ml(state: AgentState) -> str:
    if state.error:
        return "end"
    if state.cleaned_df_json and state.row_count and state.row_count >= 20:
        return "ml"
    return "end"


def _after_ml(state: AgentState) -> str:
    if state.is_time_series:
        return "forecast"
    return "anomaly"


def _after_forecast(state: AgentState) -> str:
    return "anomaly"


def _after_anomaly(state: AgentState) -> str:
    return "end"


def build_analysis_graph() -> StateGraph:
    """Build the full analysis pipeline graph."""

    # Use dict-based state for LangGraph compatibility
    def ingest_node(state: dict) -> dict:
        s = AgentState(**state)
        result = run_ingest_agent(s)
        return result.model_dump()

    def eda_node(state: dict) -> dict:
        s = AgentState(**state)
        result = run_eda_agent(s)
        return result.model_dump()

    def ml_node(state: dict) -> dict:
        s = AgentState(**state)
        result = run_ml_agent(s)
        return result.model_dump()

    def forecast_node(state: dict) -> dict:
        s = AgentState(**state)
        result = run_forecast_agent(s)
        return result.model_dump()

    def anomaly_node(state: dict) -> dict:
        s = AgentState(**state)
        result = run_anomaly_agent(s)
        return result.model_dump()

    def should_run_ml(state: dict) -> str:
        s = AgentState(**state)
        return _should_run_ml(s)

    def after_ml(state: dict) -> str:
        s = AgentState(**state)
        return _after_ml(s)

    def after_forecast(state: dict) -> str:
        return "anomaly"

    graph = StateGraph(dict)

    graph.add_node("ingest", ingest_node)
    graph.add_node("eda", eda_node)
    graph.add_node("ml", ml_node)
    graph.add_node("forecast", forecast_node)
    graph.add_node("anomaly", anomaly_node)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "eda")
    graph.add_conditional_edges("eda", should_run_ml, {"ml": "ml", "end": END})
    graph.add_conditional_edges("ml", after_ml, {"forecast": "forecast", "anomaly": "anomaly"})
    graph.add_edge("forecast", "anomaly")
    graph.add_edge("anomaly", END)

    return graph.compile()


def build_chat_graph() -> StateGraph:
    """Build the chat-only graph for NL→SQL queries."""
    def chat_node(state: dict) -> dict:
        s = AgentState(**state)
        result = run_chat_agent(s)
        return result.model_dump()

    graph = StateGraph(dict)
    graph.add_node("chat", chat_node)
    graph.set_entry_point("chat")
    graph.add_edge("chat", END)
    return graph.compile()


# Compiled graphs (singleton)
analysis_graph = build_analysis_graph()
chat_graph = build_chat_graph()
