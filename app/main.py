from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import get_connection, initialize_database
from .data_pipeline import ensure_fresh_data, refresh_data
from .schemas import CompanyOut, CompareOut, StockDataPoint, SummaryOut

app = FastAPI(
    title="Mini Financial Data Platform",
    version="1.0.0",
    description="Stock market data platform with cleaning, analytics APIs, and dashboard.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup_event() -> None:
    initialize_database()
    ensure_fresh_data()


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.post("/refresh")
def refresh() -> dict:
    return refresh_data()


@app.get("/companies", response_model=list[CompanyOut])
def companies() -> list[CompanyOut]:
    with get_connection() as conn:
        rows = conn.execute("SELECT symbol, name FROM companies ORDER BY symbol").fetchall()
    return [CompanyOut(symbol=r["symbol"], name=r["name"]) for r in rows]


@app.get("/data/{symbol}", response_model=list[StockDataPoint])
def stock_data(symbol: str, days: int = Query(30, ge=1, le=365)) -> list[StockDataPoint]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT symbol, date, open, high, low, close, volume,
                   daily_return, ma_7, high_52w, low_52w,
                   volatility_score, sentiment_index
            FROM stock_data
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (symbol.upper(), days),
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for symbol '{symbol.upper()}'")

    data = [dict(r) for r in rows]
    for item in data:
        item["date"] = pd.to_datetime(item["date"]).date()
    data.reverse()
    return [StockDataPoint(**item) for item in data]


@app.get("/summary/{symbol}", response_model=SummaryOut)
def summary(symbol: str) -> SummaryOut:
    symbol = symbol.upper()
    with get_connection() as conn:
        summary_row = conn.execute(
            """
            SELECT
                MAX(high_52w) AS high_52w,
                MIN(low_52w) AS low_52w,
                AVG(close) AS average_close,
                AVG(daily_return) AS avg_daily_return,
                MAX(date) AS latest_date
            FROM stock_data
            WHERE symbol = ?
            """,
            (symbol,),
        ).fetchone()

        if not summary_row or summary_row["high_52w"] is None:
            raise HTTPException(status_code=404, detail=f"No data found for symbol '{symbol}'")

        latest_row = conn.execute(
            """
            SELECT close, sentiment_index
            FROM stock_data
            WHERE symbol = ? AND date = ?
            """,
            (symbol, summary_row["latest_date"]),
        ).fetchone()

    return SummaryOut(
        symbol=symbol,
        high_52w=float(summary_row["high_52w"]),
        low_52w=float(summary_row["low_52w"]),
        average_close=float(summary_row["average_close"]),
        latest_close=float(latest_row["close"]),
        avg_daily_return=float(summary_row["avg_daily_return"]),
        latest_sentiment_index=float(latest_row["sentiment_index"]),
    )


@app.get("/compare", response_model=CompareOut)
def compare(
    symbol1: str = Query(..., description="Example: INFY"),
    symbol2: str = Query(..., description="Example: TCS"),
    days: int = Query(90, ge=5, le=365),
) -> CompareOut:
    s1 = symbol1.upper()
    s2 = symbol2.upper()

    query = """
        SELECT date, close
        FROM stock_data
        WHERE symbol = ?
        ORDER BY date DESC
        LIMIT ?
    """

    with get_connection() as conn:
        rows_1 = conn.execute(query, (s1, days)).fetchall()
        rows_2 = conn.execute(query, (s2, days)).fetchall()

    if not rows_1 or not rows_2:
        raise HTTPException(status_code=404, detail="One or both symbols were not found")

    df1 = pd.DataFrame([dict(r) for r in rows_1]).sort_values("date")
    df2 = pd.DataFrame([dict(r) for r in rows_2]).sort_values("date")

    merged = df1.merge(df2, on="date", how="inner", suffixes=("_1", "_2"))
    if merged.empty:
        raise HTTPException(status_code=400, detail="No overlapping dates for comparison")

    c1_start = float(merged["close_1"].iloc[0])
    c1_end = float(merged["close_1"].iloc[-1])
    c2_start = float(merged["close_2"].iloc[0])
    c2_end = float(merged["close_2"].iloc[-1])

    ret1 = (c1_end - c1_start) / c1_start if c1_start else 0.0
    ret2 = (c2_end - c2_start) / c2_start if c2_start else 0.0
    corr = float(merged["close_1"].corr(merged["close_2"]))
    winner = s1 if ret1 > ret2 else s2

    return CompareOut(
        symbol1=s1,
        symbol2=s2,
        days=len(merged),
        cumulative_return_symbol1=float(ret1),
        cumulative_return_symbol2=float(ret2),
        correlation_close=float(corr if pd.notna(corr) else 0.0),
        winner=winner,
    )
