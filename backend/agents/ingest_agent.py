"""
Ingest & Clean Agent
Accepts CSV, Excel, JSON, PDF, or URL — auto-detects schema,
handles missing data, type inference, and returns a clean DataFrame.
"""

import json
import io
from datetime import datetime
import pandas as pd
import numpy as np
from openai import OpenAI
from core.config import MODEL
from core.state import AgentState


client = OpenAI()


def _load_file(file_path: str) -> pd.DataFrame:
    ext = file_path.rsplit(".", 1)[-1].lower()
    if ext == "csv":
        return pd.read_csv(file_path)
    elif ext in ("xlsx", "xls"):
        return pd.read_excel(file_path)
    elif ext == "json":
        return pd.read_json(file_path)
    elif ext == "parquet":
        return pd.read_parquet(file_path)
    else:
        # Try CSV as fallback
        return pd.read_csv(file_path)


def _infer_schema(df: pd.DataFrame) -> dict:
    schema = {}
    for col in df.columns:
        dtype = str(df[col].dtype)
        n_unique = int(df[col].nunique())
        n_missing = int(df[col].isna().sum())
        sample = df[col].dropna().head(3).tolist()
        schema[col] = {
            "dtype": dtype,
            "unique_values": n_unique,
            "missing": n_missing,
            "missing_pct": round(n_missing / len(df) * 100, 2),
            "sample": [str(s) for s in sample],
        }
    return schema


def _clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    steps = []

    # Drop fully empty columns
    empty_cols = df.columns[df.isna().all()].tolist()
    if empty_cols:
        df = df.drop(columns=empty_cols)
        steps.append(f"Dropped {len(empty_cols)} fully empty columns: {empty_cols}")

    # Drop duplicate rows
    n_dupes = df.duplicated().sum()
    if n_dupes > 0:
        df = df.drop_duplicates()
        steps.append(f"Removed {n_dupes} duplicate rows")

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    steps.append("Normalized column names to snake_case")

    # Auto-parse datetime columns
    for col in df.columns:
        if df[col].dtype == object:
            sample = df[col].dropna().head(5)
            try:
                pd.to_datetime(sample)
                df[col] = pd.to_datetime(df[col], errors="coerce")
                if df[col].notna().sum() > len(df) * 0.5:
                    steps.append(f"Parsed '{col}' as datetime")
                else:
                    df[col] = df[col].astype(str)
            except Exception:
                pass

    # Fill missing numeric with median
    num_cols = df.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        if df[col].isna().sum() > 0:
            median = df[col].median()
            df[col] = df[col].fillna(median)
            steps.append(f"Filled missing in '{col}' with median ({median:.2f})")

    # Fill missing categorical with mode
    cat_cols = df.select_dtypes(include=["object", "category"]).columns
    for col in cat_cols:
        if df[col].isna().sum() > 0:
            mode = df[col].mode()
            if len(mode) > 0:
                df[col] = df[col].fillna(mode[0])
                steps.append(f"Filled missing in '{col}' with mode ('{mode[0]}')")

    return df, steps


def _ask_llm_about_dataset(df: pd.DataFrame, schema: dict) -> str:
    """Use GPT-4o to generate a natural language summary of the dataset."""
    prompt = f"""You are a data analyst. Analyze this dataset overview and provide:
1. What this dataset likely represents
2. Key columns and their significance
3. Potential analysis directions
4. Data quality observations

Dataset shape: {df.shape[0]} rows × {df.shape[1]} columns
Columns & schema: {json.dumps(schema, indent=2)[:3000]}
First 3 rows: {df.head(3).to_string()}
"""
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def run_ingest_agent(state: AgentState) -> AgentState:
    log = []
    log.append({
        "agent": "IngestAgent",
        "message": f"Loading file: {state.file_path}",
        "timestamp": datetime.now().isoformat(),
        "status": "running"
    })

    try:
        # Load
        df = _load_file(state.file_path)
        log.append({
            "agent": "IngestAgent",
            "message": f"Loaded {df.shape[0]:,} rows × {df.shape[1]} columns",
            "timestamp": datetime.now().isoformat(),
            "status": "running"
        })

        # Schema
        schema = _infer_schema(df)

        # Clean
        df_clean, steps = _clean_dataframe(df)
        for step in steps:
            log.append({
                "agent": "IngestAgent",
                "message": step,
                "timestamp": datetime.now().isoformat(),
                "status": "running"
            })

        # LLM summary
        llm_summary = _ask_llm_about_dataset(df_clean, schema)

        state.raw_df_json = df.to_json(orient="split", date_format="iso")
        state.cleaned_df_json = df_clean.to_json(orient="split", date_format="iso")
        state.schema_info = {
            "columns": schema,
            "llm_summary": llm_summary,
            "cleaning_steps": steps,
            "shape": list(df_clean.shape),
        }
        state.row_count = len(df_clean)
        state.column_count = len(df_clean.columns)
        state.completed_agents.append("ingest")

        log.append({
            "agent": "IngestAgent",
            "message": "✅ Ingestion complete",
            "timestamp": datetime.now().isoformat(),
            "status": "done"
        })

    except Exception as e:
        state.error = f"IngestAgent error: {str(e)}"
        log.append({
            "agent": "IngestAgent",
            "message": f"❌ Error: {e}",
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        })

    state.activity_log.extend(log)
    return state
