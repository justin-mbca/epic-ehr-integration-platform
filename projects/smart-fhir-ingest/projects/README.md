# smart_fhir_ingest — demo

This folder contains a lightweight SMART-on-FHIR ingestion demo and integration test harness designed for interviews and quick local/CI validation.

Quick layout
- `smart_fhir_ingest/ingest.py` — ingestion logic (SQLite + Postgres support)
- `smart_fhir_ingest/sample_data/patient_bundle.json` — sample FHIR bundle
- `integration_test_runner.py` — automates compose -> ingest -> verify -> teardown
- `docker-compose.yml` — demo Postgres for local integration
- `Makefile` — `make integration-test` runs the full local integration end-to-end

Run locally

1) Run unit tests (fast, uses SQLite)

```bash
cd projects/smart-fhir-ingest/projects
PYTHONPATH=. python3 -m pytest smart_fhir_ingest/tests/test_ingest.py -q
```

2) Run the full integration test locally (starts demo Postgres via docker compose)

```bash
cd projects/smart-fhir-ingest/projects
make integration-test
```

CI (GitHub Actions)

- A workflow `.github/workflows/integration-runner.yml` is included. It runs the integration runner in CI using `services.postgres` so no docker-compose is required in the job.
- The runner detects CI via `GITHUB_ACTIONS` or `CI` env and connects to the DSN supplied via `POSTGRES_DSN` (default `postgresql://demo:demo@localhost:5432/demo`).

Notes
- `psycopg2-binary` is required to run Postgres integration locally and in CI; the integration workflow installs dependencies before running the runner.
- The runner is intentionally simple to be readable during interviews; feel free to extend it to upload artifacts on failure or produce structured test reports.
