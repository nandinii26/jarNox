from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "stocks.db"

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
