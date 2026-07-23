# Energy Pipeline

ETL pipeline that collects Finnish electricity generation data from the
[Fingrid Open Data API](https://data.fingrid.fi/), stores it in PostgreSQL,
and serves it through a REST API built with FastAPI. Ingestion is orchestrated
by Apache Airflow, and the whole stack runs with a single `docker compose up`.

It ingests two sources, nuclear generation and total generation in Finland, and
exposes a derived metric: the nuclear share of total electricity generation.

## Stack

- Python 3.12
- FastAPI + Uvicorn (REST API)
- PostgreSQL 16
- Apache Airflow 2.10 (orchestration, LocalExecutor)
- Docker + Docker Compose
- `requests`, `psycopg`, `python-dotenv`

## Project structure

```
app/                      # REST API
  db.py                   # database connection
  main.py                 # FastAPI app and routes
ingestion/                # data collection
  create_table.py         # creates both tables (idempotent)
  ingest.py               # fetches one Fingrid source into PostgreSQL
dags/
  fingrid_ingest.py       # Airflow DAG that schedules the ingestion
Dockerfile                # image for the api service
Dockerfile.airflow        # Airflow image plus the ingestion dependencies
docker-compose.yml        # db + api + Airflow, one command to run it all
requirements.txt
requirements-airflow.txt  # only what the DAG needs, to avoid version clashes
```

## How it works

`ingestion/ingest.py` pulls a Fingrid dataset page by page, respecting the API
rate limit, and writes it to PostgreSQL. The source is passed as an argument
(`nuclear` for dataset 188, `total` for dataset 192), so a single script handles
every source. Inserts are idempotent: re-running never creates duplicates,
thanks to `ON CONFLICT (start_time) DO NOTHING`.

`dags/fingrid_ingest.py` runs every 10 minutes and fetches only the newest rows
each cycle. The graph is:

```
create_tables ──┬── ingest_nuclear
                └── ingest_total
```

One task per source, so the two sources run in parallel and fail independently.
Tasks are retried twice with a two-minute delay, which covers the transient 429
and network errors Fingrid occasionally returns. Catchup is disabled and only
one run is active at a time: the goal is fresh data, not a backfilled history.

`app/main.py` serves the stored data through a FastAPI service with automatic
Swagger docs. The `/generation/nuclear-share` endpoint joins both tables on the
timestamp and computes, per 3-minute interval, what percentage of total
generation came from nuclear power.

## Why Airflow

The scheduling was originally a small APScheduler worker running in its own
container. It did the job, but when a source failed all it left behind was a
line in the log. There was no run history, no automatic retry, and no way to
re-run a single failed source without restarting the whole worker.

Airflow separates the ingestion code from the questions of when it runs, how
often it is retried, and what happens on failure. Every source is a task with
its own status, its own log file per attempt, and a `Clear task` button that
re-runs just that task inside an existing run. The ingestion functions
themselves did not change; the DAG only calls them.

## Quick start (Docker)

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
Compose network the API and Airflow reach the database at host `db`; the compose
file overrides `DB_HOST` for those services, so `localhost` above is only used
when you run the code directly on your machine.

2. Build and start everything:

```bash
docker compose up --build -d
```

The first build takes a few minutes, the Airflow image is large. The
`airflow-init` container creates the metadata schema and the admin user, then
exits: seeing it in the `Exited` state is expected.

3. Open Airflow at `http://localhost:8080` and log in with `admin` / `admin`.
   New DAGs arrive paused, so switch `fingrid_ingest` on. It then runs every
   10 minutes; the play button triggers it immediately.

4. Open the interactive API docs at `http://127.0.0.1:8000/docs`.

Data is stored in a named volume, so it survives restarts. Stop the stack with
`docker compose down` (add `-v` to also wipe the volumes).

> The default credentials, the passwords in `docker-compose.yml`, and the
> exposed database port are meant for a local demo only. A real deployment
> would keep them in a secret store and put the Airflow UI behind proper auth.

## Running locally (without Docker)

Useful for development, and for running the ingestion by hand.

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

## API endpoints

| Endpoint | Description |
| --- | --- |
| `GET /` | Health check |
| `GET /generation/latest?limit=N` | Latest N nuclear generation samples |
| `GET /generation?start=&end=` | Nuclear generation over a time period |
| `GET /generation/daily?days=N` | Daily aggregates (avg, min, max) |
| `GET /generation/nuclear-share?limit=N` | Nuclear share of total generation (%) |
