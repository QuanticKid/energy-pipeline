from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from ingestion.create_table import main as create_tables
from ingestion.ingest import ingest, SOURCES

# Each cycle only needs the newest rows; ON CONFLICT drops what is already stored.
PAGES_PER_CYCLE = 3

default_args = {
    # Fingrid returns 429 under load, so a single retry covers most transient failures.
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="fingrid_ingest",
    description="Fetch Fingrid real-time generation data into PostgreSQL",
    start_date=datetime(2026, 1, 1),
    schedule="*/10 * * * *",
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["fingrid", "etl"],
) as dag:

    create = PythonOperator(
        task_id="create_tables",
        python_callable=create_tables,
    )

    for source_name in SOURCES:
        fetch = PythonOperator(
            task_id=f"ingest_{source_name}",
            python_callable=ingest,
            op_kwargs={"source_name": source_name, "pages": PAGES_PER_CYCLE},
        )
        create >> fetch