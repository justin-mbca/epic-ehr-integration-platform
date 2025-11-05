from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import json
from pathlib import Path

DEMO_ROOT = Path(__file__).parents[2]  # repo/projects/smart-fhir-ingest/projects

def run_ingest_to_postgres():
    # wrapper: read sample bundle and run ingestion to demo Postgres
    import os
    from smart_fhir_ingest.ingest import ingest_to_postgres

    # Correct path: projects/smart-fhir-ingest/projects/smart_fhir_ingest/sample_data/
    bundle_path = DEMO_ROOT / 'smart_fhir_ingest' / 'sample_data' / 'patient_bundle.json'
    with open(bundle_path, encoding='utf-8') as fh:
        bundle = json.load(fh)

    # DSN points to docker-compose demo-postgres (service hostname when run in compose)
    dsn = os.environ.get('DEMO_PG_DSN', 'postgresql://demo:demo@demo-postgres:5432/demo')
    count = ingest_to_postgres(bundle, dsn)
    print(f'Inserted {count} patients')

with DAG(
    dag_id='smart_fhir_ingest_demo',
    start_date=datetime(2024,1,1),
    schedule_interval=None,
    catchup=False,
) as dag:
    t1 = PythonOperator(
        task_id='ingest_to_postgres',
        python_callable=run_ingest_to_postgres
    )
