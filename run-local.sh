#!/usr/bin/env bash
# Convenience script to start the platform and open key URLs on macOS

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "Starting services with quick-start.sh..."
./quick-start.sh start || docker compose up -d

echo "Waiting briefly for services to warm up..."
sleep 5

echo "Opening browser windows..."
open http://localhost:3000
open http://localhost:8084/fhir/metadata

echo "Done. API Gateway: http://localhost:3000, FHIR metadata: http://localhost:8084/fhir/metadata (admin/admin123)"
