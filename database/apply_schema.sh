#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCHEMA_FILE="${SCRIPT_DIR}/schema.sql"

if [[ ! -f "${SCHEMA_FILE}" ]]; then
  echo "Schema file not found: ${SCHEMA_FILE}" >&2
  exit 1
fi

cd "${REPO_ROOT}"

echo "Applying schema from ${SCHEMA_FILE} to PostgreSQL service 'postgres'..."
docker compose -p solar-ai-support-agent exec -T postgres \
  psql -U solar -d solar_ai_support < "${SCHEMA_FILE}"

echo "Schema applied successfully."
