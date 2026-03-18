import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o"
UPLOAD_DIR = "uploads"
REPORTS_DIR = "reports"
MLFLOW_TRACKING_URI = "mlruns"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
