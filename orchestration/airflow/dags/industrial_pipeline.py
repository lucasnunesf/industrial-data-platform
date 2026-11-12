"""Batch pipeline: ERP -> bronze (ADLS) -> silver (Fabric, manual) -> gold (dbt).

Same steps as orchestration/run_pipeline.ps1, with retries, logs and history per step.
The silver notebooks run in a Fabric workspace of another tenant, which Airflow cannot
trigger, so the DAG stops and waits for a person to approve before building gold (ADR-008).
"""

from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.hitl import ApprovalOperator
from airflow.sdk import DAG

PROJECT = "/opt/project"
PIPELINE_PYTHON = "/opt/venvs/pipeline/bin/python"
DBT = "/opt/venvs/dbt/bin/dbt"

# Two Azure CLI logins, one per tenant: the lake (Azure subscription) and Fabric.
LAKE_LOGIN = "/opt/airflow/azure/lake"
FABRIC_LOGIN = "/opt/airflow/azure/fabric"

with DAG(
    dag_id="industrial_pipeline",
    description="ERP to gold, with a manual gate for the silver notebooks in Fabric",
    schedule=None,  # triggered by hand: it runs on a laptop and has a manual step
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,  # the extraction keeps its watermarks in one state file
    default_args={"retries": 1, "retry_delay": timedelta(minutes=1)},
    tags=["batch"],
) as dag:
    simulate_plant = BashOperator(
        task_id="simulate_plant",
        bash_command=f"cd {PROJECT}/simulator && {PIPELINE_PYTHON} main.py",
    )

    extract_to_bronze = BashOperator(
        task_id="extract_to_bronze",
        bash_command=f"cd {PROJECT}/ingestion && {PIPELINE_PYTHON} extract.py",
    )

    upload_to_lake = BashOperator(
        task_id="upload_to_lake",
        bash_command=f"cd {PROJECT}/ingestion && {PIPELINE_PYTHON} upload.py",
        env={"AZURE_CONFIG_DIR": LAKE_LOGIN},
        append_env=True,
    )

    wait_for_silver = ApprovalOperator(
        task_id="wait_for_silver",
        subject="Run the silver notebooks in Fabric",
        body=(
            "In the workspace idp-dev run 01_build_silver, then 02_test_silver "
            "(it must end with 0 failed). Stop the Spark sessions, then approve."
        ),
        retries=0,
    )

    build_gold = BashOperator(
        task_id="build_gold",
        bash_command=(
            f"{DBT} build --project-dir {PROJECT}/dbt --profiles-dir {PROJECT}/dbt "
            "--target-path /tmp/dbt/target --log-path /tmp/dbt/logs"
        ),
        env={"AZURE_CONFIG_DIR": FABRIC_LOGIN},
        append_env=True,
    )

    simulate_plant >> extract_to_bronze >> upload_to_lake >> wait_for_silver >> build_gold
