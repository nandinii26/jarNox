from datetime import date

from pydantic import BaseModel


class CompanyOut(BaseModel):
    symbol: str
    name: str


class StockDataPoint(BaseModel):
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    daily_return: float
    ma_7: float
    high_52w: float
    low_52w: float
    volatility_score: float
    sentiment_index: float


class SummaryOut(BaseModel):
    symbol: str
    high_52w: float
    low_52w: float
    average_close: float
    latest_close: float
    avg_daily_return: float
    latest_sentiment_index: float


class CompareOut(BaseModel):
    symbol1: str
    symbol2: str
    days: int
    cumulative_return_symbol1: float
    cumulative_return_symbol2: float
    correlation_close: float
    winner: str
