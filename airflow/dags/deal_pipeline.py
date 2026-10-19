"""
### Deal pipeline

Every day: clean the raw data with dbt, train a new sales model, and make it live
only if it is at least as good as the current one.

1. **dbt_build**: builds `stg_*` and `deal_training` and runs every dbt test. A failed
   test stops the run here, so bad data never reaches training.
2. **train_model**: trains a candidate and scores it *and* the live model on the same
   held-out deals. Saves it as a new version in `models/<version>/`. Not live yet.
3. **promote_model**: moves `models/latest.json` to the candidate if it passes the checks.
   *Skipped* (not failed) when the candidate isn't good enough: the live model keeps serving.

The Celery worker checks `models/latest.json` every few minutes and loads a new version
by itself. Each step is a plain command, so it can be run and debugged without Airflow.
"""

from datetime import datetime, timedelta, timezone

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

# Our code is mounted at /opt/app and runs in its own virtualenv (see airflow/Dockerfile)
RUN = "cd /opt/app && /opt/pipeline/bin/"

with DAG(
    dag_id="deal_pipeline",
    schedule="@daily",
    start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
    catchup=False,      # Don't run once for every missed day since start_date
    max_active_runs=1,  # Two runs at once would fight over the DuckDB file
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
    doc_md=__doc__,
    tags=["ml", "dbt"],
):
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=RUN + "dbt build --project-dir dbt --profiles-dir dbt",
    )

    train_model = BashOperator(
        task_id="train_model",
        bash_command=RUN + "python -m src.pipeline.train",
        # The last line printed (the version) is saved for the next task
        do_xcom_push=True,
    )

    promote_model = BashOperator(
        task_id="promote_model",
        bash_command=RUN + "python -m src.pipeline.promote {{ ti.xcom_pull(task_ids='train_model') }}",
        skip_on_exit_code=99,  # promote.py exits 99 when the candidate isn't good enough
        retries=0,             # Its decision doesn't change on a retry
    )

    dbt_build >> train_model >> promote_model
