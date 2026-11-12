import os
import sys
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ingestion"))

TEST_DB = "erp_test"


def _env() -> dict:
    """Database settings from .env, overridden by ERP_DB_* environment variables."""
    env = {}
    dotenv = ROOT / ".env"
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("ERP_DB_")})
    return env


@pytest.fixture(scope="session")
def db_params() -> dict:
    env = _env()
    return {
        "host": env.get("ERP_DB_HOST", "localhost"),
        "port": int(env.get("ERP_DB_PORT", "5433")),
        "user": env["ERP_DB_USER"],
        "password": env.get("ERP_DB_PASSWORD", ""),
    }


@pytest.fixture
def erp_db(db_params) -> dict:
    """A fresh ERP database (schema and seed) for each test; the real ERP is never touched."""
    with psycopg.connect(dbname="postgres", autocommit=True, **db_params) as admin:
        admin.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        admin.execute(f"CREATE DATABASE {TEST_DB}")
    params = {**db_params, "dbname": TEST_DB}
    with psycopg.connect(autocommit=True, **params) as conn:
        conn.execute((ROOT / "erp" / "schema.sql").read_text(encoding="utf-8"))
        conn.execute((ROOT / "erp" / "seed.sql").read_text(encoding="utf-8"))
    return params
