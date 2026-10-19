"""
### RAG ingest

Rebuilds the Qdrant collection from the sales PDFs in `data/` (`python -m src.models.vector`).
Runs only when triggered by hand, after the PDFs change, because it replaces the whole
collection and Qdrant Cloud Inference has usage limits.
"""

from datetime import datetime, timezone

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

with DAG(
    dag_id="rag_ingest",
    schedule=None,  # Manual only: press "Trigger" in the Airflow UI
    start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
    catchup=False,
    doc_md=__doc__,
    tags=["rag"],
):
    BashOperator(
        task_id="load_pdfs_into_qdrant",
        bash_command="cd /opt/app && /opt/pipeline/bin/python -m src.models.vector",
        retries=2,
    )
