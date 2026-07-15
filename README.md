# Energy Pipeline

Data pipeline that collects Finnish nuclear power generation from the
[Fingrid Open Data API](https://data.fingrid.fi/), stores it in PostgreSQL,
and serves it through a REST API built with FastAPI.

## Stack

- Python 3
- FastAPI + Uvicorn
- PostgreSQL 16 (running in Docker)
- `requests`, `psycopg`, `python-dotenv`

## Project structure

```
app/          # REST API
  db.py       # database connection
  main.py     # FastAPI app and routes
ingestion/    # data collection
  create_table.py
  ingest.py
```

## How it works

`ingestion/ingest.py` pulls generation data (dataset 188) from Fingrid page
by page, respecting the API rate limit, and writes it to the
`nuclear_generation` table. Inserts are idempotent: re-running the script
never creates duplicates, thanks to `ON CONFLICT (start_time) DO NOTHING`.

`app/main.py` exposes the stored data through a FastAPI service with
automatic Swagger documentation.

## Setup

1. Clone the repo and create a virtual environment:

```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1     # Windows
   source .venv/bin/activate      # Linux / macOS
```

2. Install dependencies:

```bash
   pip install -r requirements.txt
```

3. Start PostgreSQL in Docker:

```bash
   docker run --name energy-db -e POSTGRES_PASSWORD=energy123 -e POSTGRES_DB=energy -p 5432:5432 -d postgres:16
```

4. Create a `.env` file in the project root:

```
   FINGRID_API_KEY=your_api_key_here
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=energy
   DB_USER=postgres
   DB_PASSWORD=energy123
```

## Usage

Create the table and collect data:

```bash
python -m ingestion.create_table
python -m ingestion.ingest
```

Run the API:

```bash
fastapi dev app/main.py
```

Then open the interactive docs at `http://127.0.0.1:8000/docs`.

## API endpoints

| Endpoint | Description |
| --- | --- |
| `GET /` | Health check |
| `GET /generation/latest?limit=N` | Latest N generation samples |
| `GET /generation?start=&end=` | Generation over a time period |
| `GET /generation/daily?days=N` | Daily aggregates (avg, min, max) |