from app.db import get_connection

SCHEMA = """
CREATE TABLE IF NOT EXISTS nuclear_generation (
    start_time TIMESTAMPTZ PRIMARY KEY,
    end_time   TIMESTAMPTZ,
    value_mw   NUMERIC
)
"""


def main() -> None:
    with get_connection() as conn:
        conn.execute(SCHEMA)
    print("Table nuclear_generation is ready")


if __name__ == "__main__":
    main()