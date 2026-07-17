import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from ingestion.ingest import ingest, SOURCES
from ingestion.create_table import main as create_tables

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# How often to poll Fingrid. Data refreshes every 3 min, so 10 is plenty.
INTERVAL_MINUTES = int(os.environ.get("INGEST_INTERVAL_MINUTES", "10"))

# Each cycle only needs the newest rows; ON CONFLICT drops everything already stored.
PAGES_PER_CYCLE = 3


def collect_all() -> None:
    for source in SOURCES:
        try:
            ingest(source, pages=PAGES_PER_CYCLE)
        except Exception:
            # One failing source (API down, network blip) must not kill the worker.
            log.exception("Ingest failed for source %s", source)


def main() -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(collect_all, "interval", minutes=INTERVAL_MINUTES)
    log.info("Scheduler started, collecting every %s min", INTERVAL_MINUTES)

    create_tables()  # make sure tables exist before the first collection
    collect_all()  # run once now instead of waiting for the first interval
    scheduler.start()


if __name__ == "__main__":
    main()