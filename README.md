# DataMind AI — Autonomous Multi-Agent Data Intelligence Platform

<div align="center">

![DataMind AI](https://img.shields.io/badge/DataMind-AI-6366f1?style=for-the-badge&logo=lightning&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=next.js&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-FF6B6B?style=for-the-badge)
![GPT-4o](https://img.shields.io/badge/GPT--4o-Powered-10A37F?style=for-the-badge&logo=openai&logoColor=white)

**Drop any dataset. Seven AI agents analyze it autonomously.**

</div>

---

## What is DataMind AI?

DataMind AI is a production-grade, autonomous data intelligence platform powered by **7 specialized AI agents** orchestrated via **LangGraph**. Upload a CSV, Excel, or JSON file — the agents spin up in sequence, each building on the previous agent's work, delivering a complete end-to-end analysis with zero manual configuration.

This is not a wrapper around a single LLM call. Each agent is an autonomous unit with its own tools, memory, and decision-making. The orchestrator routes between agents based on the data's characteristics (e.g., skipping forecasting for non-time-series data).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      LangGraph Orchestrator                  │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │  Ingest  │──▶│   EDA    │──▶│    ML    │──▶│Forecast │ │
│  │  Agent   │   │  Agent   │   │  Agent   │   │  Agent  │ │
│  └──────────┘   └──────────┘   └──────────┘   └─────────┘ │
│                                      │               │      │
│                               ┌──────────┐   ┌──────────┐ │
│                               │ Anomaly  │   │  Chat    │ │
│                               │  Agent   │   │  Agent   │ │
│                               └──────────┘   └──────────┘ │
└─────────────────────────────────────────────────────────────┘
         ↕  WebSocket  ↕
┌─────────────────────────────────────────────────────────────┐
│                   Next.js 14 Frontend                        │
│  Live Agent Feed │ Interactive Charts │ NL→SQL Chat          │
└─────────────────────────────────────────────────────────────┘
```

---

## The 7 AI Agents

| Agent | What it Does |
|-------|-------------|
| **IngestAgent** | Loads CSV/Excel/JSON/PDF, auto-detects schema, cleans data, fills missing values, generates NL summary via GPT-4o |
| **EDAAgent** | Computes statistics, IQR outlier detection, correlations, generates 10+ interactive Plotly charts, AI insights |
| **MLAgent** | Auto-selects target column & task type, trains RandomForest/XGBoost/GradientBoosting/Logistic, cross-validates, SHAP explainability, MLflow tracking |
| **ForecastAgent** | Detects datetime columns, runs Prophet forecasting (30-day horizon), confidence intervals, trend analysis |
| **AnomalyAgent** | Isolation Forest with contamination tuning, anomaly score distribution, 2D scatter with anomaly markers |
| **ChatAgent** | NL → SQL pipeline on in-memory SQLite, auto-generates charts for visualization queries, multi-turn chat history |
| **Orchestrator** | LangGraph StateGraph with conditional routing — skips ML if <20 rows, skips forecasting for non-time-series |

---

## Tech Stack

### Backend
- **Python 3.11** with FastAPI + WebSockets
- **LangGraph** for multi-agent orchestration
- **OpenAI GPT-4o** for all LLM reasoning
- **scikit-learn, XGBoost** for ML
- **Prophet** for time series forecasting
- **Isolation Forest** for anomaly detection
- **SHAP** for ML explainability
- **MLflow** for experiment tracking
- **Pydantic v2** for shared agent state

### Frontend
- **Next.js 14** App Router with TypeScript
- **Tailwind CSS** glassmorphism dark theme
- **Framer Motion** for animations
- **Plotly.js** for interactive charts
- **Zustand** for state management
- **WebSockets** for real-time agent activity streaming
- **React Markdown** for AI-generated insights

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key

### 1. Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt

# Create .env
echo "OPENAI_API_KEY=your_key_here" > .env

PYTHONPATH=. uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 3. Open App
Navigate to **http://localhost:3000** and drop any CSV/Excel/JSON file.

### Windows One-Click Start
```bash
start.bat
```

---

## Docker Deployment

```bash
# Copy and fill in your API key
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

docker-compose up --build
```

---

## Key Features

- **Real-time Agent Feed** — Watch each agent work via WebSocket streaming, see status updates as they happen
- **Zero Configuration** — Drop a file, the AI figures out everything: target column, task type, chart types
- **Interactive Dashboard** — Tabbed view with Overview, EDA, ML Performance, Forecast, Anomaly tabs
- **Natural Language SQL** — Ask questions in plain English, get SQL + results + auto-generated charts
- **SHAP Explainability** — Understand which features drive ML predictions with waterfall charts
- **Export Ready** — All charts are interactive Plotly figures with download capabilities

---

## Project Structure

```
datamind-ai/
├── backend/
│   ├── agents/
│   │   ├── ingest_agent.py      # Data loading & cleaning
│   │   ├── eda_agent.py         # Exploratory data analysis
│   │   ├── ml_agent.py          # AutoML training
│   │   ├── forecast_agent.py    # Time series forecasting
│   │   ├── anomaly_agent.py     # Anomaly detection
│   │   ├── chat_agent.py        # NL→SQL chat
│   │   └── orchestrator.py      # LangGraph state machine
│   ├── api/
│   │   └── main.py              # FastAPI + WebSocket server
│   ├── core/
│   │   ├── config.py            # Global settings
│   │   └── state.py             # Pydantic AgentState
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Main page
│   │   └── layout.tsx           # Root layout
│   ├── components/
│   │   ├── UploadZone.tsx       # Drag & drop upload
│   │   ├── AgentFeed.tsx        # Real-time activity log
│   │   ├── ResultsDashboard.tsx # Tabbed results view
│   │   └── ChatPanel.tsx        # NL→SQL chat interface
│   └── lib/
│       └── store.ts             # Zustand state management
├── docker-compose.yml
├── start.bat                    # Windows quick start
└── README.md
```

---

## Demo

### How it Works

```
1. Drop a CSV/Excel/JSON file onto the upload zone
2. Seven agents activate automatically via LangGraph
3. Watch the real-time agent feed on the right panel
4. Explore results across 5 dashboard tabs
5. Ask questions in plain English via the chat panel
```

### Agent Pipeline (live output)

```
⚡ IngestAgent    → "Loaded 891 rows, 12 columns. Parsed 'date' as datetime.
                     Filled 177 missing values in 'Age' with median (28.0)"

⚡ EDAAgent       → "Computed stats for 7 numeric columns.
                     Generated 9 interactive charts. Strong correlation:
                     Fare ↔ Survived (0.26)"

⚡ MLAgent        → "Task: Classification | Target: Survived
                     Best model: XGBoost (accuracy: 0.821)
                     SHAP: Sex, Pclass, Age are top predictors"

⚡ ForecastAgent  → "Detected datetime column: date
                     30-day Prophet forecast generated.
                     Trend: upward (+12.3%)"

⚡ AnomalyAgent   → "Isolation Forest detected 44 anomalies (4.9%)
                     Risk Assessment: MEDIUM — fare outliers detected"
```

### NL→SQL Chat

```
You:   "What is the average fare by passenger class?"
SQL:   SELECT Pclass, AVG(Fare) as avg_fare FROM data GROUP BY Pclass
Chart: Auto-generated bar chart ✓

You:   "Show me survival rate by gender"
SQL:   SELECT Sex, AVG(Survived) as survival_rate FROM data GROUP BY Sex
Chart: Auto-generated bar chart ✓
```

### Suggested Datasets to Try

| Dataset | What you'll see |
|---------|----------------|
| [Titanic](https://www.kaggle.com/datasets/titanicpassengers) | Classification, SHAP, survival patterns |
| [Sales data](https://www.kaggle.com/datasets/retail-sales) | Forecasting, revenue trends, anomalies |
| [Iris](https://archive.ics.uci.edu/ml/datasets/iris) | Multi-class classification, EDA |
| Any CSV you have | Full autonomous analysis |

> **Note:** Add screenshots/GIFs here after recording a demo session.

---

## About

Built as a showcase of modern AI engineering — multi-agent orchestration, real-time streaming, autonomous decision-making, and production-quality UI.

**Author:** Abdul Lathif Syed | [GitHub: SAbdulLathif01](https://github.com/SAbdulLathif01)

---

<div align="center">
⭐ Star this repo if you found it useful!
</div>
