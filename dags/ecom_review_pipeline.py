from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
from load_to_firestore import main as load_to_firestore_main

# Default arguments for all tasks
default_args = {
    'owner': 'Ragiri Himadeep',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2)
}

# DAG definition
with DAG(
    dag_id='ecom_review_pipeline',
    default_args=default_args,
    start_date=datetime(2023, 1, 1),
    schedule='@daily',
    catchup=False
) as dag:

    # Task 1: Extract
    extract = SparkSubmitOperator(
        task_id='extract_reviews',
        conn_id='spark_local',
        application='/opt/airflow/spark_jobs/extract_reviews.py',
    )

    # Task 2: Transform
    transform = SparkSubmitOperator(
        task_id='transform_reviews',
        conn_id='spark_local',
        application='/opt/airflow/spark_jobs/transform_reviews.py',
    )

    # Task 3: Load to Firestore
    load = PythonOperator(
        task_id='load_to_firestore',
        python_callable=load_to_firestore_main,
    )

    # Task 4: Launch Streamlit app
    launch_streamlit = BashOperator(
        task_id='launch_streamlit_dashboard',
        bash_command=(
            "streamlit run /opt/airflow/streamlit_app/app.py "
            "--server.port 8501 --server.address 0.0.0.0 "
            "--server.headless true &"
        )
    )

    # Define task dependencies
    extract >> transform >> load >> launch_streamlit