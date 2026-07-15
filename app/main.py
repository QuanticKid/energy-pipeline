from datetime import datetime

from fastapi import FastAPI, Query, HTTPException

from app.db import get_connection

app = FastAPI(title="Energy Pipeline API")

LATEST_SQL = """
SELECT start_time, end_time, value_mw
FROM nuclear_generation
ORDER BY start_time DESC
LIMIT %s
"""


@app.get("/")
def root():
    return {"status": "ok", "service": "energy-pipeline"}


@app.get("/generation/latest")
def latest_generation(limit: int = 10):
    with get_connection() as conn:
        rows = conn.execute(LATEST_SQL, (limit,)).fetchall()

    return [
        {"start_time": start, "end_time": end, "value_mw": value}
        for start, end, value in rows
    ]
RANGE_SQL = """
SELECT start_time, end_time, value_mw
FROM nuclear_generation
WHERE start_time >= %s AND start_time < %s
ORDER BY start_time
"""


@app.get("/generation")
def generation_range(
    start: datetime = Query(..., description="Start of the period (inclusive)"),
    end: datetime = Query(..., description="End of the period (exclusive)"),
):
    if start >= end:
        raise HTTPException(status_code=400, detail="start must be before end")

    with get_connection() as conn:
        rows = conn.execute(RANGE_SQL, (start, end)).fetchall()

    return {
        "start": start,
        "end": end,
        "count": len(rows),
        "data": [
            {"start_time": s, "end_time": e, "value_mw": v}
            for s, e, v in rows
        ],
    }
DAILY_AVG_SQL = """
SELECT
    date_trunc('day', start_time) AS day,
    AVG(value_mw) AS avg_mw,
    MIN(value_mw) AS min_mw,
    MAX(value_mw) AS max_mw,
    COUNT(*) AS samples
FROM nuclear_generation
GROUP BY day
ORDER BY day DESC
LIMIT %s
"""


@app.get("/generation/daily")
def daily_average(days: int = 7):
    with get_connection() as conn:
        rows = conn.execute(DAILY_AVG_SQL, (days,)).fetchall()

    return [
        {
            "day": day.date(),
            "avg_mw": round(float(avg), 2),
            "min_mw": float(min_mw),
            "max_mw": float(max_mw),
            "samples": samples,
        }
        for day, avg, min_mw, max_mw, samples in rows
    ]