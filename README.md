# Energy Pipeline

Ingestion pipeline that collects Finnish nuclear power generation data
from the [Fingrid Open Data API](https://data.fingrid.fi/) and stores it
in PostgreSQL.

## Stack

- Python 3
- PostgreSQL 16 (running in Docker)
- `requests`, `psycopg`, `python-dotenv`

## How it works

`ingest.py` pulls generation data (dataset 188) page by page, respecting
the API rate limit, and writes it to the `nuclear_generation` table. Inserts
are idempotent: re-running the script never creates duplicates, thanks to
`ON CONFLICT (start_time) DO NOTHING`.

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
   docker run --name energy-db \
     -e POSTGRES_PASSWORD=energy123 \
     -e POSTGRES_DB=energy \
     -p 5432:5432 -d postgres:16
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

```bash
python create_table.py   # create the table
python ingest.py         # fetch and store data
python read_data.py      # check what's in the database
```