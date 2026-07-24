import os

import pytest

from app.db import get_connection
from ingestion.create_table import main as create_tables

# The DB-backed tests only run where a PostgreSQL instance is available.
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DB_TESTS") != "1",
    reason="set RUN_DB_TESTS=1 to run tests that need PostgreSQL",
)

ROWS = [
    ("2026-01-01T00:00:00+00:00", "2026-01-01T00:03:00+00:00", 100.0),
    ("2026-01-01T00:03:00+00:00", "2026-01-01T00:06:00+00:00", 110.0),
]

INSERT = """
INSERT INTO nuclear_generation (start_time, end_time, value_mw)
VALUES (%s, %s, %s)
ON CONFLICT (start_time) DO NOTHING
"""


@pytest.fixture
def clean_table():
    create_tables()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM nuclear_generation")
        conn.commit()
    yield


def insert_rows() -> int:
    inserted = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for row in ROWS:
                cur.execute(INSERT, row)
                inserted += cur.rowcount
        conn.commit()
    return inserted


def test_first_insert_writes_every_row(clean_table):
    assert insert_rows() == len(ROWS)


def test_second_insert_writes_nothing(clean_table):
    insert_rows()

    assert insert_rows() == 0


def test_row_count_stays_the_same(clean_table):
    insert_rows()
    insert_rows()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM nuclear_generation")
            count = cur.fetchone()[0]

    assert count == len(ROWS)