import os

import psycopg


def connect() -> psycopg.Connection:
    return psycopg.connect(
        host=os.getenv("ERP_DB_HOST", "localhost"),
        port=int(os.getenv("ERP_DB_PORT", "5433")),
        dbname=os.environ["ERP_DB_NAME"],
        user=os.environ["ERP_DB_USER"],
        password=os.getenv("ERP_DB_PASSWORD", ""),
    )
