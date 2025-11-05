import sqlite3
import tempfile
import json
import os
from smart_fhir_ingest.ingest import ingest_bundle


def test_ingest_bundle():
    here = os.path.dirname(__file__)
    data_path = os.path.join(here, '..', 'sample_data', 'patient_bundle.json')
    data_path = os.path.normpath(data_path)

    with open(data_path, encoding='utf-8') as fh:
        bundle = json.load(fh)

    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    conn = sqlite3.connect(tmp.name)
    count = ingest_bundle(bundle, conn)
    assert count == 2

    cur = conn.cursor()
    cur.execute('SELECT id, given, family FROM patients ORDER BY id')
    rows = cur.fetchall()
    assert rows[0][1] == 'John'
    assert rows[1][1] == 'Jane'
