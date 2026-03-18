import os
from pathlib import Path
from dotenv import load_dotenv

# Load from backend/.env first, then fall back to project root .env
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o"
UPLOAD_DIR = "uploads"
REPORTS_DIR = "reports"
MLFLOW_TRACKING_URI = "mlruns"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
