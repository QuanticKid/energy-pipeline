import argparse
import logging
import os
import time

import requests
from dotenv import load_dotenv
from psycopg import sql

from app.db import get_connection

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

API_KEY = os.environ["FINGRID_API_KEY"]

# One place that describes every source. Both are 3-minute real-time series
# with the same columns, so they differ only by dataset id and target table.
SOURCES = {
    "nuclear": {"dataset_id": 188, "table": "nuclear_generation"},
    "total": {"dataset_id": 192, "table": "total_generation"},
}

PAGES_TO_FETCH = 20
PER_PAGE = 100
REQUEST_DELAY = 7       # pause between pages to stay under the rate limit
RATE_LIMIT_WAIT = 20    # pause after hitting a 429
MAX_RETRIES = 5

# %s binds values, but it cannot bind an identifier like a table name.
# The table comes from our own SOURCES map (never user input), and
# sql.Identifier quotes it safely, so this stays injection-proof.
INSERT_TEMPLATE = sql.SQL("""
INSERT INTO {table} (start_time, end_time, value_mw)
VALUES (%s, %s, %s)
ON CONFLICT (start_time) DO NOTHING
""")


def fetch_page(session: requests.Session, dataset_id: int, page: int) -> list[dict]:
    url = f"https://data.fingrid.fi/api/datasets/{dataset_id}/data"
    params = {"page": page, "pageSize": PER_PAGE}
    for _ in range(MAX_RETRIES):
        response = session.get(url, params=params)
        if response.status_code == 429:
            log.warning("Page %s: rate limited, waiting %ss", page, RATE_LIMIT_WAIT)
            time.sleep(RATE_LIMIT_WAIT)
            continue
        response.raise_for_status()
        return response.json()["data"]
    raise RuntimeError(f"Page {page}: still rate limited after {MAX_RETRIES} retries")


def ingest(source_name: str, pages: int = PAGES_TO_FETCH) -> None:
    source = SOURCES[source_name]
    dataset_id = source["dataset_id"]
    insert_sql = INSERT_TEMPLATE.format(table=sql.Identifier(source["table"]))

    session = requests.Session()
    session.headers["x-api-key"] = API_KEY

    inserted = 0
    with get_connection() as conn:
        for page in range(1, pages + 1):
            records = fetch_page(session, dataset_id, page)
            if not records:
                log.info("Page %s: no more data, stopping", page)
                break

            with conn.cursor() as cur:
                for r in records:
                    cur.execute(insert_sql, (r["startTime"], r["endTime"], r["value"]))
                    inserted += cur.rowcount
            conn.commit()

            log.info("Page %s done, new rows so far: %s", page, inserted)
            time.sleep(REQUEST_DELAY)

    log.info("Finished %s. New rows inserted: %s", source_name, inserted)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a Fingrid dataset into PostgreSQL")
    parser.add_argument("source", choices=SOURCES.keys(), help="which source to ingest")
    args = parser.parse_args()
    ingest(args.source)


if __name__ == "__main__":
    main()