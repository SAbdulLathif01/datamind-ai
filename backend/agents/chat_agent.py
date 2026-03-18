"""
Chat Agent — Natural Language → SQL → Results → Visualization
Multi-turn conversational interface over the uploaded dataset.
"""

import json
import sqlite3
import tempfile
import os
from datetime import datetime
import pandas as pd
import plotly.express as px
from openai import OpenAI
from core.config import MODEL
from core.state import AgentState

client = OpenAI()

# In-memory SQLite per session
_db_connections: dict[str, tuple[sqlite3.Connection, str]] = {}


def _get_or_create_db(session_id: str, df: pd.DataFrame) -> sqlite3.Connection:
    if session_id not in _db_connections:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        df.to_sql("dataset", conn, if_exists="replace", index=False)
        _db_connections[session_id] = conn
    return _db_connections[session_id]


def _df_from_state(state: AgentState) -> pd.DataFrame:
    data = json.loads(state.cleaned_df_json)
    df = pd.DataFrame(data["data"], columns=data["columns"])
    for col in df.columns:
        if df[col].dtype == object:
            sample = df[col].dropna().head(5)
            try:
                parsed = pd.to_datetime(sample)
                if parsed.notna().all():
                    df[col] = pd.to_datetime(df[col], errors="coerce")
            except Exception:
                pass
    return df


def _nl_to_sql(question: str, schema: dict, chat_history: list[dict]) -> str:
    col_desc = "\n".join([
        f"  - {col}: {info['dtype']}, {info['unique_values']} unique values, sample: {info['sample']}"
        for col, info in schema.get("columns", {}).items()
    ])

    history_str = "\n".join([
        f"{m['role'].upper()}: {m['content']}" for m in chat_history[-6:]
    ])

    prompt = f"""You are a SQL expert. Convert the user question to SQLite SQL query.

Table name: dataset
Columns:
{col_desc}

Recent conversation:
{history_str}

User question: {question}

Rules:
- Return ONLY the SQL query, no explanation
- Use SQLite syntax
- Limit results to 100 rows unless user asks for more
- Use column names exactly as listed above
"""
    response = client.chat.completions.create(
        model=MODEL, max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    sql = response.choices[0].message.content.strip()
    # Clean markdown code blocks
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


def _execute_sql(conn: sqlite3.Connection, sql: str) -> tuple[pd.DataFrame, str]:
    try:
        result_df = pd.read_sql_query(sql, conn)
        return result_df, None
    except Exception as e:
        return None, str(e)


def _generate_chart_if_needed(question: str, result_df: pd.DataFrame) -> dict | None:
    """Decide if a chart would be useful and generate it."""
    if result_df is None or len(result_df) == 0:
        return None

    keywords = ["trend", "over time", "distribution", "compare", "breakdown",
                 "chart", "plot", "visualize", "by", "group", "top", "bottom"]
    if not any(k in question.lower() for k in keywords):
        return None

    num_cols = result_df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = result_df.select_dtypes(exclude=["number"]).columns.tolist()

    try:
        if len(result_df.columns) == 2 and len(cat_cols) >= 1 and len(num_cols) >= 1:
            fig = px.bar(result_df, x=cat_cols[0], y=num_cols[0],
                          template="plotly_dark", color_discrete_sequence=["#6366f1"])
            return json.loads(fig.to_json())
        elif len(num_cols) >= 2:
            fig = px.scatter(result_df, x=num_cols[0], y=num_cols[1],
                              template="plotly_dark", color_discrete_sequence=["#f59e0b"])
            return json.loads(fig.to_json())
        elif len(num_cols) == 1:
            fig = px.histogram(result_df, x=num_cols[0], template="plotly_dark",
                                color_discrete_sequence=["#8b5cf6"])
            return json.loads(fig.to_json())
    except Exception:
        return None
    return None


def _generate_natural_response(question: str, sql: str,
                                 result_df: pd.DataFrame, error: str) -> str:
    if error:
        prompt = f"The SQL query failed with error: {error}. Question was: {question}. Provide a helpful response explaining the issue."
    else:
        result_preview = result_df.head(10).to_string() if result_df is not None else "No results"
        prompt = f"""You are a data analyst assistant. The user asked: "{question}"

SQL executed: {sql}
Result ({len(result_df)} rows):
{result_preview}

Provide a clear, concise natural language answer. Include key numbers and insights.
If the result is a table, summarize the key findings in 2-3 sentences.
"""
    response = client.chat.completions.create(
        model=MODEL, max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def run_chat_agent(state: AgentState) -> AgentState:
    """Process a single chat turn — NL → SQL → Result → Natural Response."""
    log = []
    log.append({"agent": "ChatAgent", "message": f"Processing: {state.user_query[:50]}...",
                 "timestamp": datetime.now().isoformat(), "status": "running"})
    try:
        df = _df_from_state(state)
        conn = _get_or_create_db(state.session_id, df)

        # Generate SQL
        sql = _nl_to_sql(state.user_query, state.schema_info or {}, state.chat_history)
        state.sql_query = sql
        log.append({"agent": "ChatAgent", "message": f"SQL: {sql[:80]}...",
                     "timestamp": datetime.now().isoformat(), "status": "running"})

        # Execute
        result_df, error = _execute_sql(conn, sql)

        # Generate chart
        chart = _generate_chart_if_needed(state.user_query, result_df)

        # Natural language response
        nl_response = _generate_natural_response(state.user_query, sql, result_df, error)

        # Build result
        result_data = {
            "sql": sql,
            "answer": nl_response,
            "row_count": len(result_df) if result_df is not None else 0,
            "table": result_df.head(50).to_dict(orient="records") if result_df is not None else [],
            "chart": chart,
            "error": error,
        }
        state.query_result = json.dumps(result_data)

        # Update chat history
        state.chat_history.append({"role": "user", "content": state.user_query})
        state.chat_history.append({"role": "assistant", "content": nl_response})

        log.append({"agent": "ChatAgent", "message": "✅ Query answered",
                     "timestamp": datetime.now().isoformat(), "status": "done"})

    except Exception as e:
        state.query_result = json.dumps({"error": str(e), "answer": f"Sorry, I encountered an error: {e}"})
        log.append({"agent": "ChatAgent", "message": f"❌ Error: {e}",
                     "timestamp": datetime.now().isoformat(), "status": "error"})

    state.activity_log.extend(log)
    return state
