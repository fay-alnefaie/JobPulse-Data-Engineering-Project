from datetime import datetime

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator


with DAG(
    dag_id="docker_test",
    start_date=datetime(2026, 9, 21),
    schedule=None,
    catchup=False,
    tags=["jobpulse", "test"],
) as dag:

    test_docker = DockerOperator(
        task_id="test_docker",
        image="hello-world",
        command=None,
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        auto_remove="success",
    )