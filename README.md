# Mini Financial Data Platform

A small end-to-end stock analytics platform built with FastAPI, SQLite, Pandas, and a React dashboard.

## Features

- Collects stock data from `yfinance` (with automatic mock-data fallback).
- Cleans and transforms data using Pandas.
- Computes required metrics:
  - `Daily Return = (CLOSE - OPEN) / OPEN`
  - 7-day moving average (`ma_7`)
  - 52-week high/low (`high_52w`, `low_52w`)
- Adds custom metrics:
  - `volatility_score` (annualized rolling volatility)
  - `sentiment_index` (mock momentum-based index)
- Exposes REST APIs with automatic Swagger docs (`/docs`).
- Includes a React browser dashboard (served by FastAPI) with company list, chart, range filter, and stock comparison.

## Project Structure

```text
jarx/
  app/
    config.py
    database.py
    data_pipeline.py
    schemas.py
    main.py
  static/
    index.html
  data/
    stocks.db (auto-created)
  requirements.txt
  README.md
```

## Setup

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Open:
- Dashboard: `http://127.0.0.1:8000/`
- Swagger: `http://127.0.0.1:8000/docs`

## API Endpoints

- `GET /companies` - list available companies
- `GET /data/{symbol}?days=30` - recent stock data (default 30 days)
- `GET /summary/{symbol}` - 52-week high/low and summary stats
- `GET /compare?symbol1=INFY&symbol2=TCS&days=90` - comparison between two stocks
- `POST /refresh` - force re-fetch/rebuild data

## Notes

- By default, symbols include: `INFY`, `TCS`, `RELIANCE`, `HDFCBANK`, `ICICIBANK`.
- Startup uses seeded mock data first so the app can boot reliably in serverless deployments.
- The `POST /refresh` endpoint still attempts live `yfinance` fetches and falls back to mock data if the network is blocked or rate-limited.
