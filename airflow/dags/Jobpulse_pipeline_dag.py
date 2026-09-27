"""
JobPulse Pipeline DAG
=====================
Orchestrates the project's real data flow: Extract (Sabbar/Tanqeeb/GulfTalent) -> Load -> Transform (dbt).

Before running:
1. Build the scraper image once (from src/scraper):
       docker build -t jobpulse-scraper:latest .
2. Make sure docker-compose.yaml uses a relative path for the dags volume, not an absolute one.
"""

from datetime import datetime, timedelta

from airflow.sdk import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import TaskGroup
from docker.types import Mount

default_args = {
    "owner": "jobpulse_team",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Path to the dbt project inside the Airflow container
# (requires mounting the dbt/ folder into the Airflow containers via docker-compose)
DBT_PROJECT_DIR = "/opt/airflow/dbt/jobpulse_dbt"

# Named Docker volume (Docker manages where this actually lives on disk,
# so there's no machine-specific absolute path to keep in sync across the team).
# Docker creates it automatically the first time it's used.
scraper_mounts = [
    Mount(
        source="jobpulse_raw_data",
        target="/App/data/raw_data",
        type="volume",
    )
]

with DAG(
    dag_id="jobpulse_pipeline",
    description="Extract (scrapers) -> Load -> Transform (dbt) for JobPulse",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["jobpulse", "production"],
) as dag:

    with TaskGroup(group_id="extract") as extract_group:

        # NOTE: execution_timeout must stay generous (hours, not minutes).
        # Sabbar alone needs 600+ listing pages plus thousands of per-job
        # detail requests with 10 concurrent workers -- comfortably over
        # 30 minutes. A short timeout here reproduces the exact failure
        # we already diagnosed (AirflowTaskTimeout while the scraper was
        # still legitimately working).
        scrape_sabbar = DockerOperator(
            task_id="scrape_sabbar",
            image="jobpulse-scraper:latest",
            command="python sabbar_scraper.py",
            docker_url="unix://var/run/docker.sock",
            network_mode="bridge",
            # "force" avoids the HTTP 409 "container is running" conflict
            # if this task ever does hit the timeout: force-remove kills
            # the container first instead of erroring on cleanup.
            auto_remove="force",
            mount_tmp_dir=False,
            mounts=scraper_mounts,
            execution_timeout=timedelta(hours=3),
        )

        scrape_tanqeeb = DockerOperator(
            task_id="scrape_tanqeeb",
            image="jobpulse-scraper:latest",
            command="python tanqeeb_scraper.py",
            docker_url="unix://var/run/docker.sock",
            network_mode="bridge",
            auto_remove="force",
            mount_tmp_dir=False,
            mounts=scraper_mounts,
            execution_timeout=timedelta(hours=3),
        )

        scrape_gulftalent = DockerOperator(
            task_id="scrape_gulftalent",
            image="jobpulse-scraper:latest",
            command="python gulftalent_scraper.py",
            docker_url="unix://var/run/docker.sock",
            network_mode="bridge",
            auto_remove="force",
            mount_tmp_dir=False,
            mounts=scraper_mounts,
            execution_timeout=timedelta(hours=3),
        )

    upload_to_blob = DockerOperator(
        task_id="upload_to_blob",
        image="jobpulse-scraper:latest",
        command="python upload_to_blob.py",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        auto_remove="force",
        mount_tmp_dir=False,
        mounts=scraper_mounts,
        # Service Principal credentials, provided via Airflow Variables
        # (Admin -> Variables), never hardcoded here.
        environment={
            "AZURE_TENANT_ID": "{{ var.value.azure_tenant_id }}",
            "AZURE_CLIENT_ID": "{{ var.value.azure_client_id }}",
            "AZURE_CLIENT_SECRET": "{{ var.value.azure_client_secret }}",
            "AZURE_STORAGE_ACCOUNT_NAME": "{{ var.value.azure_storage_account_name }}",
        },
    )

    # Reuses the Snowflake connection already configured in dbt's profiles.yml,
    # so no separate credentials need to be managed for this step.
    copy_into_snowflake = BashOperator(
        task_id="copy_into_snowflake",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt run-operation load_raw_files",
    )

    dbt_run_core = BashOperator(
        task_id="dbt_run_core",
        # Builds everything up through int_jobs_final, which extract_skills.py needs to read from.
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt run -s +int_jobs_final",
    )
    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt snapshot",
    )
    extract_skills = DockerOperator(
        task_id="extract_skills",
        image="jobpulse-nlp:latest",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        auto_remove="force",
        mount_tmp_dir=False,
        execution_timeout=timedelta(hours=2),
        # Snowflake credentials, provided via Airflow Variables (Admin -> Variables),
        # never hardcoded here.
        environment={
            "SNOWFLAKE_ACCOUNT": "{{ var.value.snowflake_account }}",
            "SNOWFLAKE_USER": "{{ var.value.snowflake_user }}",
            "SNOWFLAKE_PASSWORD": "{{ var.value.snowflake_password }}",
            "SNOWFLAKE_ROLE": "JOBPULSE_DEVELOPER",
            "SNOWFLAKE_WAREHOUSE": "JOBPULSE_WH",
            "SNOWFLAKE_DATABASE": "JOBPULSE_DB",
            "SNOWFLAKE_SCHEMA": "RAW",
        },
    )
    dbt_run_marts = BashOperator(
        task_id="dbt_run_marts",
        # Only what's strictly downstream of int_jobs_final (the marts) -
        # everything upstream was already built by dbt_run_core.
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt run -s int_jobs_final+ --exclude int_jobs_final",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt test",
    )

    extract_group >> upload_to_blob >> copy_into_snowflake >> dbt_run_core >> dbt_snapshot >> extract_skills >> dbt_run_marts >> dbt_test