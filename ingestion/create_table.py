from app.db import get_connection

# Both datasets share the same shape, so the schemas are identical.
NUCLEAR_SCHEMA = """
CREATE TABLE IF NOT EXISTS nuclear_generation (
    start_time TIMESTAMPTZ PRIMARY KEY,
    end_time   TIMESTAMPTZ,
    value_mw   NUMERIC
)
"""

TOTAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS total_generation (
    start_time TIMESTAMPTZ PRIMARY KEY,
    end_time   TIMESTAMPTZ,
    value_mw   NUMERIC
)
"""


def main() -> None:
    with get_connection() as conn:
        conn.execute(NUCLEAR_SCHEMA)
        conn.execute(TOTAL_SCHEMA)
    print("Tables nuclear_generation and total_generation are ready")


if __name__ == "__main__":
    main()