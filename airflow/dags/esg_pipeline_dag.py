# File: airflow/dags/esg_pipeline_dag.py

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# Base path where the project is mounted inside the Airflow container
PROJECT_DIR = "/opt/airflow/esg_project"

default_args = {
    "owner": "ishan",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="esg_data_pipeline",
    description="ESG Data Platform: extract -> clean -> validate -> gold layer",
    default_args=default_args,
    schedule=None,          # manual trigger only for now; we'll add scheduling later
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["esg", "portfolio-project"],
) as dag:

    extract_pdf = BashOperator(
        task_id="extract_pdf",
        bash_command=f"cd {PROJECT_DIR} && python src/extract/pdf_extractor.py",
    )

    clean_pdf = BashOperator(
        task_id="clean_pdf",
        bash_command=f"cd {PROJECT_DIR} && python src/clean/pdf_cleaner.py",
    )

    validate_pdf = BashOperator(
        task_id="validate_pdf",
        bash_command=f"cd {PROJECT_DIR} && python -m src.validate.validate_pdf_data",
    )

    build_gold_layer = BashOperator(
        task_id="build_gold_layer",
        bash_command=f"cd {PROJECT_DIR} && python -m src.validate.build_gold_layer",
    )

    # ---- Define task dependencies (the actual pipeline order) ----
    extract_pdf >> clean_pdf >> validate_pdf >> build_gold_layer