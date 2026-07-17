# Energy Pipeline

ETL pipeline that collects Finnish electricity generation data from the
[Fingrid Open Data API](https://data.fingrid.fi/), stores it in PostgreSQL,
and serves it through a REST API built with FastAPI. A background worker keeps
the database up to date on a schedule, and the whole stack runs with a single
`docker compose up`.

It ingests two sources, nuclear generation and total generation in Finland, and
exposes a derived metric: the nuclear share of total electricity generation.

## Stack

- Python 3.12
- FastAPI + Uvicorn (REST API)
- PostgreSQL 16
- APScheduler (background ingestion)
- Docker + Docker Compose
- `requests`, `psycopg`, `python-dotenv`

## Project structure

```
app/                    # REST API
  db.py                 # database connection
  main.py               # FastAPI app and routes
ingestion/              # data collection
  create_table.py       # creates both tables (idempotent)
  ingest.py             # fetches one Fingrid source into PostgreSQL
  scheduler.py          # background worker, polls Fingrid on a schedule
Dockerfile              # image shared by the api and worker services
docker-compose.yml      # db + api + worker, one command to run it all
requirements.txt
```

## How it works

`ingestion/ingest.py` pulls a Fingrid dataset page by page, respecting the API
rate limit, and writes it to PostgreSQL. The source is passed as an argument
(`nuclear` for dataset 188, `total` for dataset 192), so a single script handles
every source. Inserts are idempotent: re-running never creates duplicates,
thanks to `ON CONFLICT (start_time) DO NOTHING`.

`ingestion/scheduler.py` is a background worker. On start it makes sure the
tables exist, then polls both sources every few minutes, fetching only the
newest rows each cycle. A failure in one source is logged and does not stop the
worker.

`app/main.py` serves the stored data through a FastAPI service with automatic
Swagger docs. The `/generation/nuclear-share` endpoint joins both tables on the
timestamp and computes, per 3-minute interval, what percentage of total
generation came from nuclear power.

## Quick start (Docker)

This runs the database, the API, and the worker together.

1. Create a `.env` file in the project root:

```
FINGRID_API_KEY=your_api_key_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=energy
DB_USER=postgres
DB_PASSWORD=energy123
```

Get a free API key at [data.fingrid.fi](https://data.fingrid.fi/). Inside the
Compose network the API and worker reach the database at host `db`; the compose
file overrides `DB_HOST` for those services, so `localhost` above is only used
when you run the code directly on your machine.

2. Build and start everything:

```bash
docker compose up --build
```

3. Open the interactive docs at `http://127.0.0.1:8000/docs`.

The worker starts filling the database immediately and refreshes it every
10 minutes. Data is stored in a named volume, so it survives restarts. Stop the
stack with `docker compose down` (add `-v` to also wipe the data volume).

## Running locally (without Docker)

Useful for development.

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1     # Windows
source .venv/bin/activate      # Linux / macOS
pip install -r requirements.txt
```

2. Start PostgreSQL in Docker:

```bash
docker run --name energy-db -e POSTGRES_PASSWORD=energy123 -e POSTGRES_DB=energy -p 5432:5432 -d postgres:16
```

3. Create the tables and collect data for each source:

```bash
python -m ingestion.create_table
python -m ingestion.ingest nuclear
python -m ingestion.ingest total
```

4. Run the API:

```bash
fastapi dev app/main.py
```

Optionally run the background worker instead of collecting by hand:

```bash
python -m ingestion.scheduler
```

## API endpoints

| Endpoint | Description |
| --- | --- |
| `GET /` | Health check |
| `GET /generation/latest?limit=N` | Latest N nuclear generation samples |
| `GET /generation?start=&end=` | Nuclear generation over a time period |
| `GET /generation/daily?days=N` | Daily aggregates (avg, min, max) |
| `GET /generation/nuclear-share?limit=N` | Nuclear share of total generation (%) |