from db import get_connection

COUNT_SQL = "SELECT COUNT(*) FROM nuclear_generation"

LATEST_SQL = """
SELECT start_time, value_mw
FROM nuclear_generation
ORDER BY start_time DESC
LIMIT 5
"""


def main() -> None:
    with get_connection() as conn:
        total = conn.execute(COUNT_SQL).fetchone()[0]
        latest = conn.execute(LATEST_SQL).fetchall()

    print(f"Total rows: {total}\n")
    for start_time, value_mw in latest:
        print(f"{start_time}  ->  {value_mw} MW")


if __name__ == "__main__":
    main()