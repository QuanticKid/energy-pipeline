import pytest
from airflow.models import DagBag


@pytest.fixture(scope="module")
def dagbag() -> DagBag:
    # include_examples=False keeps Airflow's bundled demo DAGs out of the run.
    return DagBag(dag_folder="/opt/airflow/dags", include_examples=False)


def test_no_import_errors(dagbag):
    assert dagbag.import_errors == {}


def test_dag_is_registered(dagbag):
    assert "fingrid_ingest" in dagbag.dags


def test_expected_tasks(dagbag):
    dag = dagbag.dags["fingrid_ingest"]
    assert set(dag.task_ids) == {"create_tables", "ingest_nuclear", "ingest_total"}


def test_ingest_tasks_depend_on_create_tables(dagbag):
    dag = dagbag.dags["fingrid_ingest"]
    create = dag.get_task("create_tables")

    downstream = {task.task_id for task in create.downstream_list}

    assert downstream == {"ingest_nuclear", "ingest_total"}


def test_retries_configured(dagbag):
    # Without retries a transient Fingrid error would mark the run failed.
    dag = dagbag.dags["fingrid_ingest"]

    for task in dag.tasks:
        assert task.retries > 0