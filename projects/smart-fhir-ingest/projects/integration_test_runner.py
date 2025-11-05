#!/usr/bin/env python3
"""Integration test runner for the smart_fhir_ingest demo.

Flow:
 - Start demo Postgres via docker compose
 - Wait for Postgres to accept connections
 - Run ingest_to_postgres against the demo DB
 - Verify row count
 - Tear down compose (remove volumes)
"""
import subprocess
import sys
import time
import os
from pathlib import Path

ROOT = Path(__file__).parent
COMPOSE_FILE = ROOT / 'docker-compose.yml'

def run(cmd, **kwargs):
    print('RUN:', ' '.join(cmd))
    subprocess.check_call(cmd, **kwargs)

def wait_for_postgres(ci_mode=False, dsn=None, timeout=30):
    """Wait for Postgres to be ready.

    - In non-CI mode we call `docker exec ... pg_isready` against the compose container.
    - In CI mode we try connecting via psycopg2 to the provided DSN (or localhost:5432).
    """
    start = time.time()
    if ci_mode:
        # try to connect using psycopg2 to the DSN
        import psycopg2
        while time.time() - start < timeout:
            try:
                conn = psycopg2.connect(dsn)
                conn.close()
                return True
            except Exception:
                time.sleep(0.5)
        return False

    # legacy: docker compose container readiness
    while time.time() - start < timeout:
        try:
            subprocess.check_call(['docker', 'exec', 'projects-demo-postgres-1', 'pg_isready', '-U', 'demo'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            time.sleep(0.5)
        except Exception:
            time.sleep(0.5)
    return False

def main():
    # Decide if running in CI (GitHub Actions) - if so, skip compose and use provided DSN
    ci_mode = os.environ.get('CI', '').lower() == 'true' or os.environ.get('GITHUB_ACTIONS', '').lower() == 'true'
    dsn = os.environ.get('POSTGRES_DSN', 'postgresql://demo:demo@localhost:15433/demo')

    try:
        if not ci_mode:
            run(['docker', 'compose', '-f', str(COMPOSE_FILE), 'up', '-d'])
            print('Waiting for Postgres...')
            if not wait_for_postgres():
                print('Postgres did not become ready in time', file=sys.stderr)
                sys.exit(2)
            target_dsn = 'postgresql://demo:demo@localhost:15433/demo'
        else:
            print('CI mode detected; skipping docker-compose and using service DSN')
            target_dsn = os.environ.get('POSTGRES_DSN', 'postgresql://demo:demo@localhost:5432/demo')
            print('Waiting for Postgres service...')
            if not wait_for_postgres(ci_mode=True, dsn=target_dsn, timeout=60):
                print('Postgres service did not become ready in time', file=sys.stderr)
                sys.exit(2)

        # run ingestion
        sys.path.insert(0, str(ROOT))
        from smart_fhir_ingest.ingest import ingest_to_postgres
        bundle = json_load(ROOT / 'smart_fhir_ingest' / 'sample_data' / 'patient_bundle.json')
        count = ingest_to_postgres(bundle, target_dsn)
        print('Inserted', count)

        # verify via psycopg2 when in CI, otherwise via psql in container
        if ci_mode:
            import psycopg2
            conn = psycopg2.connect(target_dsn)
            cur = conn.cursor()
            cur.execute('select count(*) from patients')
            print('count', cur.fetchone()[0])
            cur.close()
            conn.close()
        else:
            out = subprocess.check_output([
                'docker', 'exec', 'projects-demo-postgres-1', 'psql', '-U', 'demo', '-d', 'demo', '-c', "select count(*) from patients;"
            ])
            print(out.decode())
    finally:
        if not ci_mode:
            run(['docker', 'compose', '-f', str(COMPOSE_FILE), 'down', '-v'])

def json_load(p: Path):
    import json
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)

if __name__ == '__main__':
    main()
