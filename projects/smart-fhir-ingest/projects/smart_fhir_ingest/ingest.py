import argparse
import json
import sqlite3
import os
from urllib.parse import urlparse
from typing import Dict, Any


def parse_patient(resource: Dict[str, Any]) -> Dict[str, Any]:
    # Basic mapping from FHIR Patient to analytics row
    pid = resource.get('id') or resource.get('identifier', [{}])[0].get('value')
    name = resource.get('name', [{}])[0]
    given = ' '.join(name.get('given', [])) if name else ''
    family = name.get('family') if name else ''
    birth = resource.get('birthDate')
    gender = resource.get('gender')

    return {
        'id': pid,
        'given': given,
        'family': family,
        'birthDate': birth,
        'gender': gender
    }


def ingest_bundle(bundle: Dict[str, Any], conn: sqlite3.Connection):
    entries = bundle.get('entry', [])
    patients = []
    for e in entries:
        res = e.get('resource')
        if not res:
            continue
        if res.get('resourceType') == 'Patient':
            patients.append(parse_patient(res))

    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS patients (
        id TEXT PRIMARY KEY,
        given TEXT,
        family TEXT,
        birthDate TEXT,
        gender TEXT
    )
    ''')

    for p in patients:
        cur.execute('''
        INSERT OR REPLACE INTO patients (id, given, family, birthDate, gender)
        VALUES (?,?,?,?,?)
        ''', (p['id'], p['given'], p['family'], p['birthDate'], p['gender']))

    conn.commit()
    return len(patients)


def ingest_to_postgres(bundle: Dict[str, Any], pg_dsn: str):
    """Ingest patients from a FHIR bundle into Postgres.

    pg_dsn: a libpq-style DSN or postgres URL, e.g. postgres://user:pass@host:5432/dbname
    Returns number of patients inserted.
    """
    # import here to avoid failing if psycopg2 isn't installed for sqlite-only runs
    import psycopg2

    entries = bundle.get('entry', [])
    patients = []
    for e in entries:
        res = e.get('resource')
        if not res:
            continue
        if res.get('resourceType') == 'Patient':
            patients.append(parse_patient(res))

    # Parse URL style DSN if provided
    if pg_dsn.startswith('postgres'):
        url = urlparse(pg_dsn)
        user = url.username
        password = url.password
        host = url.hostname
        port = url.port or 5432
        dbname = url.path.lstrip('/')
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
    else:
        conn = psycopg2.connect(pg_dsn)

    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS patients (
        id TEXT PRIMARY KEY,
        given TEXT,
        family TEXT,
        birthDate TEXT,
        gender TEXT
    )
    ''')

    for p in patients:
        cur.execute('''
        INSERT INTO patients (id, given, family, birthDate, gender)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO UPDATE SET
          given = EXCLUDED.given,
          family = EXCLUDED.family,
          birthDate = EXCLUDED.birthDate,
          gender = EXCLUDED.gender
        ''', (p['id'], p['given'], p['family'], p['birthDate'], p['gender']))

    conn.commit()
    cur.close()
    conn.close()
    return len(patients)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--db', required=True)
    args = parser.parse_args()

    with open(args.input, encoding='utf-8') as fh:
        bundle = json.load(fh)

    # Support sqlite (file path) or postgres URL
    db_target = args.db
    if db_target.startswith('postgres') or db_target.startswith('postgresql'):
        count = ingest_to_postgres(bundle, db_target)
        print(f'Imported {count} patients into Postgres')
    else:
        conn = sqlite3.connect(db_target)
        count = ingest_bundle(bundle, conn)
        print(f'Imported {count} patients into SQLite')


if __name__ == '__main__':
    main()
