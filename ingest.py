import logging
import os
import time

import requests
from dotenv import load_dotenv

from db import get_connection

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

FINGRID_URL = "https://data.fingrid.fi/api/datasets/188/data"
API_KEY = os.environ["FINGRID_API_KEY"]

PAGES_TO_FETCH = 20
PER_PAGE = 100
REQUEST_DELAY = 7       # pause between pages to stay under the rate limit
RATE_LIMIT_WAIT = 20    # pause after hitting a 429
MAX_RETRIES = 5

INSERT_SQL = """
INSERT INTO nuclear_generation (start_time, end_time, value_mw)
VALUES (%s, %s, %s)
ON CONFLICT (start_time) DO NOTHING
"""


def fetch_page(session: requests.Session, page: int) -> list[dict]:
    params = {"page": page, "pageSize": PER_PAGE}
    for _ in range(MAX_RETRIES):
        response = session.get(FINGRID_URL, params=params)
        if response.status_code == 429:
            log.warning("Page %s: rate limited, waiting %ss", page, RATE_LIMIT_WAIT)
            time.sleep(RATE_LIMIT_WAIT)
            continue
        response.raise_for_status()
        return response.json()["data"]
    raise RuntimeError(f"Page {page}: still rate limited after {MAX_RETRIES} retries")


def main() -> None:
    session = requests.Session()
    session.headers["x-api-key"] = API_KEY

    inserted = 0
    with get_connection() as conn:
        for page in range(1, PAGES_TO_FETCH + 1):
            records = fetch_page(session, page)
            if not records:
                log.info("Page %s: no more data, stopping", page)
                break

            with conn.cursor() as cur:
                for r in records:
                    cur.execute(INSERT_SQL, (r["startTime"], r["endTime"], r["value"]))
                    inserted += cur.rowcount
            conn.commit()

            log.info("Page %s done, new rows so far: %s", page, inserted)
            time.sleep(REQUEST_DELAY)

    log.info("Finished. New rows inserted: %s", inserted)


if __name__ == "__main__":
    main()