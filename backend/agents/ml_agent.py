"""
ML Agent
Auto-selects the best model, trains, evaluates with cross-validation,
explains with SHAP, and tracks experiments with MLflow.
"""

import json
import warnings
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
from sklearn.metrics import (classification_report, accuracy_score, f1_score,
                              mean_squared_error, r2_score, roc_auc_score)
import xgboost as xgb
import shap
import mlflow
import mlflow.sklearn
from openai import OpenAI
from core.config import MODEL, MLFLOW_TRACKING_URI
from core.state import AgentState

warnings.filterwarnings("ignore")
client = OpenAI()
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


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


def _select_target_with_llm(df: pd.DataFrame) -> tuple[str, str]:
    """Ask GPT-4o which column is the best target and what task type."""
    n = len(df)
    cols_info = {
        col: {
            "dtype": str(df[col].dtype),
            "nunique": int(df[col].nunique()),
            "sample": df[col].dropna().head(3).tolist(),
            "is_id_like": df[col].nunique() >= n * 0.95
        }
        for col in df.columns
    }
    available_cols = list(df.columns)
    prompt = f"""Given these dataset columns, identify the best target variable for ML prediction and the task type.

Available columns (you MUST pick EXACTLY one of these): {available_cols}

Column details: {json.dumps(cols_info, default=str)}
Dataset shape: {df.shape}

Rules:
- You MUST return a column name that is in the Available columns list above — no exceptions
- NEVER pick ID columns (is_id_like=true) or columns with all unique values
- NEVER pick columns that look like identifiers (e.g. passengerid, id, index, name, ticket)
- For classification: pick binary or low-cardinality columns (nunique <= 20)
- For regression: pick continuous numeric columns
- Prefer columns that are clearly outcome/target variables (e.g. survived, price, sales, churn)

Return JSON only:
{{"target_column": "column_name", "task_type": "classification|regression", "reasoning": "brief reason"}}"""

    response = client.chat.completions.create(
        model=MODEL, max_tokens=200,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}]
    )
    result = json.loads(response.choices[0].message.content)
    target = result["target_column"]
    task_type = result["task_type"]

    # Validate the LLM picked an actual column (case-insensitive match)
    col_lower = {c.lower(): c for c in df.columns}
    if target not in df.columns:
        if target.lower() in col_lower:
            target = col_lower[target.lower()]  # fix case mismatch
        else:
            # Fallback: heuristic — best non-ID numeric column
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            candidates = [c for c in numeric_cols if df[c].nunique() < len(df) * 0.95]
            if not candidates:
                candidates = numeric_cols
            if not candidates:
                raise ValueError(f"LLM chose non-existent target '{target}' and no numeric fallback found")
            target = candidates[-1]
            task_type = "classification" if df[target].nunique() <= 20 else "regression"

    return target, task_type


def _prepare_features(df: pd.DataFrame, target: str, task_type: str) -> tuple:
    X = df.drop(columns=[target])
    y = df[target]

    # Drop datetime columns from features
    X = X.select_dtypes(exclude=["datetime64"])

    # Drop ID-like columns (all unique or nearly all unique, non-target)
    n = len(X)
    id_cols = [c for c in X.columns if X[c].nunique() >= n * 0.95]
    if id_cols:
        X = X.drop(columns=id_cols)

    # Drop high-cardinality text columns (e.g. name, ticket, cabin)
    high_card = [c for c in X.select_dtypes(include=["object"]).columns
                 if X[c].nunique() > 50]
    if high_card:
        X = X.drop(columns=high_card)

    # Encode remaining categoricals
    le_map = {}
    for col in X.select_dtypes(include=["object", "category"]).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
        le_map[col] = le

    # Always LabelEncode target for classification (fixes XGBoost [1,2,3] vs [0,1,2])
    if task_type == "classification":
        le_y = LabelEncoder()
        y = le_y.fit_transform(y.astype(str))
    else:
        y = y.values

    # Fill any remaining NaNs in X
    X = X.fillna(X.median(numeric_only=True))
    X = X.fillna(0)

    return X, y, le_map


def _train_models(X_train, X_test, y_train, y_test, task_type: str) -> dict:
    results = {}

    if task_type == "classification":
        models = {
            "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
            "XGBoost": xgb.XGBClassifier(n_estimators=100, random_state=42, eval_metric="logloss", verbosity=0),
            "GradientBoosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
            "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        }
        for name, model in models.items():
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            acc = accuracy_score(y_test, preds)
            f1 = f1_score(y_test, preds, average="weighted", zero_division=0)
            cv = cross_val_score(model, X_train, y_train, cv=3, scoring="accuracy").mean()
            results[name] = {"model": model, "accuracy": round(acc, 4),
                              "f1": round(f1, 4), "cv_score": round(cv, 4),
                              "score": round(f1, 4)}
    else:
        models = {
            "RandomForest": RandomForestRegressor(n_estimators=100, random_state=42),
            "XGBoost": xgb.XGBRegressor(n_estimators=100, random_state=42, verbosity=0),
            "GradientBoosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "Ridge": Ridge(alpha=1.0),
        }
        for name, model in models.items():
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
            r2 = float(r2_score(y_test, preds))
            cv = cross_val_score(model, X_train, y_train, cv=3, scoring="r2").mean()
            results[name] = {"model": model, "rmse": round(rmse, 4),
                              "r2": round(r2, 4), "cv_score": round(cv, 4),
                              "score": round(r2, 4)}

    return results


def _compute_shap(model, X_test: pd.DataFrame, task_type: str) -> dict:
    try:
        sample = X_test.head(100)
        if hasattr(model, "feature_importances_"):
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(sample)
        else:
            explainer = shap.LinearExplainer(model, sample)
            shap_values = explainer.shap_values(sample)

        # Handle multi-class (list of arrays) or 3D arrays
        if isinstance(shap_values, list):
            # Multi-class: average absolute SHAP across all classes
            shap_values = np.mean([np.abs(sv) for sv in shap_values], axis=0)
        elif shap_values.ndim == 3:
            shap_values = np.abs(shap_values).mean(axis=2)

        mean_shap = np.abs(shap_values).mean(axis=0)
        feature_importance = dict(zip(sample.columns, [round(float(v), 4) for v in mean_shap]))
        return dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
    except Exception:
        # Fallback to built-in feature importance
        if hasattr(model, "feature_importances_"):
            imp = dict(zip(X_test.columns, [round(float(v), 4) for v in model.feature_importances_]))
            return dict(sorted(imp.items(), key=lambda x: x[1], reverse=True))
        return {}


def _log_to_mlflow(run_name: str, model, metrics: dict, task_type: str):
    try:
        with mlflow.start_run(run_name=run_name):
            mlflow.log_params({"task_type": task_type, "model": run_name})
            for k, v in metrics.items():
                if k != "model":
                    mlflow.log_metric(k, v)
            mlflow.sklearn.log_model(model, "model")
    except Exception:
        pass  # MLflow optional


def run_ml_agent(state: AgentState) -> AgentState:
    log = []
    log.append({"agent": "MLAgent", "message": "Starting ML pipeline...",
                 "timestamp": datetime.now().isoformat(), "status": "running"})
    try:
        df = _df_from_state(state)
        if len(df) < 20:
            raise ValueError("Dataset too small for ML (need 20+ rows)")

        # Select target
        log.append({"agent": "MLAgent", "message": "Identifying target variable with AI...",
                     "timestamp": datetime.now().isoformat(), "status": "running"})
        target, task_type = _select_target_with_llm(df)

        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found in dataset")

        log.append({"agent": "MLAgent",
                     "message": f"Target: '{target}' | Task: {task_type}",
                     "timestamp": datetime.now().isoformat(), "status": "running"})

        # Prepare
        X, y, _ = _prepare_features(df, target, task_type)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y if task_type == "classification" else None)

        # Train all models
        log.append({"agent": "MLAgent", "message": "Training 4 models in parallel...",
                     "timestamp": datetime.now().isoformat(), "status": "running"})
        results = _train_models(X_train, X_test, y_train, y_test, task_type)

        # Pick best
        best_name = max(results, key=lambda k: results[k]["score"])
        best = results[best_name]

        log.append({"agent": "MLAgent",
                     "message": f"Best model: {best_name} (score: {best['score']})",
                     "timestamp": datetime.now().isoformat(), "status": "running"})

        # SHAP feature importance
        log.append({"agent": "MLAgent", "message": "Computing SHAP feature importance...",
                     "timestamp": datetime.now().isoformat(), "status": "running"})
        shap_importance = _compute_shap(best["model"], X_test, task_type)

        # MLflow
        _log_to_mlflow(best_name, best["model"],
                        {k: v for k, v in best.items() if k != "model"}, task_type)

        # Build results (exclude model object, not serializable)
        all_results_clean = {}
        for name, r in results.items():
            all_results_clean[name] = {k: v for k, v in r.items() if k != "model"}

        state.ml_results = {
            "task_type": task_type,
            "target_column": target,
            "best_model": best_name,
            "all_models": all_results_clean,
            "feature_importance_shap": shap_importance,
            "train_size": len(X_train),
            "test_size": len(X_test),
        }
        state.best_model_name = best_name
        state.feature_importance = shap_importance
        state.completed_agents.append("ml")

        log.append({"agent": "MLAgent", "message": "✅ ML pipeline complete",
                     "timestamp": datetime.now().isoformat(), "status": "done"})

    except Exception as e:
        # Don't set state.error — let downstream agents (anomaly) still run
        state.ml_results = {"error": str(e)}
        log.append({"agent": "MLAgent", "message": f"❌ Error: {e}",
                     "timestamp": datetime.now().isoformat(), "status": "error"})

    state.activity_log.extend(log)
    return state
