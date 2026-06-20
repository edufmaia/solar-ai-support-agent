"""Apply database/schema.sql to a PostgreSQL instance, standalone (no Docker).

Reads the connection string from DATABASE_URL (the SQLAlchemy form
`postgresql+psycopg://...` is accepted and normalized). The schema is
idempotent (`IF NOT EXISTS`), so re-applying is safe. Used by CI; locally the
Docker helpers (apply_schema.ps1 / apply_schema.sh) remain the convenient path.

Usage:
    DATABASE_URL=postgresql://solar:solar_password@localhost:5432/solar_ai_support \
        python database/apply_schema.py
"""

import os
import sys
from pathlib import Path

import psycopg

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def main() -> int:
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1

    dsn = dsn.replace("postgresql+psycopg://", "postgresql://")
    sql = SCHEMA_PATH.read_text(encoding="utf-8")

    conn = psycopg.connect(dsn, autocommit=True)
    try:
        conn.execute(sql)
    finally:
        conn.close()

    print(f"Schema applied from {SCHEMA_PATH.name} ({len(sql)} bytes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
