# SMART-on-FHIR Ingest Demo

Small demo that ingests a FHIR Patient Bundle (JSON) and writes a simplified patient table into SQLite.

This is a lightweight project intended for portfolio/demo use. It does not require running an Epic sandbox.

Usage
------
1. Run locally against a FHIR bundle file:

```bash
python -m projects.smart_fhir_ingest.ingest --input sample_data/patient_bundle.json --db ./data/smart_ingest.db
```

2. Inspect the SQLite database:

```bash
sqlite3 ./data/smart_ingest.db "SELECT id, given, family, birthDate, gender FROM patients;"
```

Why this is useful
-------------------
- Demonstrates FHIR parsing and mapping to analytics schema.
- Lightweight, runnable locally (no external FHIR server required).
- Easy to extend to Postgres, Airflow, or dbt in a production pipeline.

Files
-----
- `ingest.py` - ingestion script and functions
- `sample_data/patient_bundle.json` - sample FHIR bundle (Synthea-like)
- `tests/test_ingest.py` - unit test for ingestion
- `requirements.txt` - optional dependencies (none required for this demo)
