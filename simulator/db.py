import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def connect() -> psycopg.Connection:
    return psycopg.connect(
        host=os.getenv("ERP_DB_HOST", "localhost"),
        port=int(os.getenv("ERP_DB_PORT", "5433")),
        dbname=os.environ["ERP_DB_NAME"],
        user=os.environ["ERP_DB_USER"],
        password=os.getenv("ERP_DB_PASSWORD", ""),
    )


def lookup(conn, table: str, code_col: str, id_col: str) -> dict:
    rows = conn.execute(f"SELECT {code_col}, {id_col} FROM {table}").fetchall()
    return dict(rows)
