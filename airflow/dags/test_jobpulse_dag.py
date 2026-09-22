from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime


def test_jobpulse():
    print("JobPulse Airflow is working!")


with DAG(
    dag_id="test_jobpulse",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    test_task = PythonOperator(
        task_id="test_task",
        python_callable=test_jobpulse,
    )