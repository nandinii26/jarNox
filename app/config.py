import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def _serverless_data_dir() -> Path:
    if os.getenv("VERCEL") or os.getenv("NETLIFY") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return Path(tempfile.gettempdir()) / "jarx"
    return DATA_DIR


DB_PATH = _serverless_data_dir() / "stocks.db"

DEFAULT_SYMBOLS = [
    "INFY.NS",
    "TCS.NS",
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
]

SYMBOL_NAME_MAP = {
    "INFY": "Infosys",
    "TCS": "Tata Consultancy Services",
    "RELIANCE": "Reliance Industries",
    "HDFCBANK": "HDFC Bank",
    "ICICIBANK": "ICICI Bank",
}
