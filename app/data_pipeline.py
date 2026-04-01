from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .config import DEFAULT_SYMBOLS, SYMBOL_NAME_MAP
from .database import get_connection, initialize_database


def _safe_symbol_name(yf_symbol: str) -> str:
    core = yf_symbol.split(".")[0]
    return SYMBOL_NAME_MAP.get(core, core)


def _clean_dataframe(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if df.empty:
        return df

    # Normalize column names from provider output.
    df = df.reset_index().rename(
        columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )

    required_cols = ["date", "open", "high", "low", "close", "volume"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = np.nan

    df["symbol"] = symbol.split(".")[0]

   
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df[numeric_cols] = df[numeric_cols].interpolate(method="linear", limit_direction="both")
    df[numeric_cols] = df[numeric_cols].ffill().bfill()

    df = df.dropna(subset=["date", "open", "close"]).sort_values("date")

   
    df["daily_return"] = np.where(df["open"] != 0, (df["close"] - df["open"]) / df["open"], 0.0)
    df["ma_7"] = df["close"].rolling(window=7, min_periods=1).mean()
    df["high_52w"] = df["high"].rolling(window=252, min_periods=1).max()
    df["low_52w"] = df["low"].rolling(window=252, min_periods=1).min()

   
    daily_pct = df["close"].pct_change().fillna(0)
    df["volatility_score"] = daily_pct.rolling(window=14, min_periods=2).std().fillna(0) * np.sqrt(252)

   
    momentum = df["close"].pct_change(periods=5).fillna(0)
    df["sentiment_index"] = (50 + momentum * 500).clip(lower=0, upper=100)

    return df[
        [
            "symbol",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "daily_return",
            "ma_7",
            "high_52w",
            "low_52w",
            "volatility_score",
            "sentiment_index",
        ]
    ]


def _build_mock_data(symbol: str, days: int = 400) -> pd.DataFrame:
    np.random.seed(abs(hash(symbol)) % (2**32 - 1))
    end_date = datetime.utcnow().date()
    dates = pd.bdate_range(end=end_date, periods=days)

    base_price = np.random.uniform(500, 2500)
    returns = np.random.normal(loc=0.0005, scale=0.018, size=len(dates))
    prices = base_price * np.cumprod(1 + returns)

    close = np.round(prices, 2)
    open_ = np.round(close * (1 + np.random.normal(0, 0.004, len(dates))), 2)
    high = np.round(np.maximum(open_, close) * (1 + np.random.uniform(0.001, 0.015, len(dates))), 2)
    low = np.round(np.minimum(open_, close) * (1 - np.random.uniform(0.001, 0.015, len(dates))), 2)
    volume = np.random.randint(200000, 6000000, len(dates))

    df = pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )
    df["symbol"] = symbol.split(".")[0]
    return _clean_dataframe(df, symbol)


def _fetch_yfinance(symbol: str, period: str = "2y") -> pd.DataFrame:
    try:
        import yfinance as yf
    except Exception:
        return pd.DataFrame()

    try:
        df = yf.download(symbol, period=period, auto_adjust=False, progress=False)
        return _clean_dataframe(df, symbol)
    except Exception:
        return pd.DataFrame()


def upsert_company_metadata(symbols: list[str]) -> None:
    with get_connection() as conn:
        for yf_symbol in symbols:
            symbol = yf_symbol.split(".")[0]
            conn.execute(
                """
                INSERT INTO companies (symbol, name)
                VALUES (?, ?)
                ON CONFLICT(symbol) DO UPDATE SET name = excluded.name
                """,
                (symbol, _safe_symbol_name(yf_symbol)),
            )
        conn.commit()


def upsert_stock_data(df: pd.DataFrame) -> int:
    if df.empty:
        return 0

    records = [
        (
            r.symbol,
            str(r.date),
            float(r.open),
            float(r.high),
            float(r.low),
            float(r.close),
            float(r.volume),
            float(r.daily_return),
            float(r.ma_7),
            float(r.high_52w),
            float(r.low_52w),
            float(r.volatility_score),
            float(r.sentiment_index),
        )
        for r in df.itertuples(index=False)
    ]

    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO stock_data (
                symbol, date, open, high, low, close, volume,
                daily_return, ma_7, high_52w, low_52w,
                volatility_score, sentiment_index
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, date) DO UPDATE SET
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                volume = excluded.volume,
                daily_return = excluded.daily_return,
                ma_7 = excluded.ma_7,
                high_52w = excluded.high_52w,
                low_52w = excluded.low_52w,
                volatility_score = excluded.volatility_score,
                sentiment_index = excluded.sentiment_index
            """,
            records,
        )
        conn.commit()
    return len(records)


def refresh_data(symbols: list[str] | None = None) -> dict:
    initialize_database()
    symbols = symbols or DEFAULT_SYMBOLS
    upsert_company_metadata(symbols)

    inserted = 0
    sources = {}
    for yf_symbol in symbols:
        df = _fetch_yfinance(yf_symbol)
        source = "yfinance"
        if df.empty:
            df = _build_mock_data(yf_symbol)
            source = "mock"

        inserted += upsert_stock_data(df)
        sources[yf_symbol.split(".")[0]] = source

    return {"rows_upserted": inserted, "sources": sources, "symbols": [s.split(".")[0] for s in symbols]}


def latest_data_date() -> datetime.date | None:
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(date) AS max_date FROM stock_data").fetchone()
    if row and row["max_date"]:
        return datetime.strptime(row["max_date"], "%Y-%m-%d").date()
    return None


def ensure_fresh_data(max_age_days: int = 1) -> dict:
    latest = latest_data_date()
    if latest is None:
        return refresh_data()

    if datetime.utcnow().date() - latest >= timedelta(days=max_age_days):
        return refresh_data()

    return {"rows_upserted": 0, "sources": {}, "status": "already_fresh"}
