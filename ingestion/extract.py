"""Incremental extraction from the ERP (PostgreSQL) to Parquet files (bronze).

Mutable tables are pulled by updated_at, append-only tables by primary key.
Bronze is append-only: a row updated twice shows up in two files, and silver
keeps the latest version. Delivery is at-least-once (state is saved after each
table's file is written).
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pyarrow as pa
import pyarrow.parquet as pq

from config import TABLES, Table
from db import connect

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
TS_UTC = pa.timestamp("us", tz="UTC")


def arrow_type(data_type: str, precision: int | None, scale: int | None) -> pa.DataType:
    if data_type == "integer":
        return pa.int32()
    if data_type == "bigint":
        return pa.int64()
    if data_type == "smallint":
        return pa.int16()
    if data_type == "numeric":
        return pa.decimal128(precision, scale)
    if data_type in ("character varying", "character", "text"):
        return pa.string()
    if data_type == "date":
        return pa.date32()
    if data_type == "timestamp with time zone":
        return TS_UTC
    raise ValueError(f"Unmapped Postgres type: {data_type}")


def table_schema(conn: psycopg.Connection, table_name: str) -> pa.Schema:
    rows = conn.execute(
        """
        SELECT column_name, data_type, numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    ).fetchall()
    return pa.schema([(name, arrow_type(dtype, prec, scale)) for name, dtype, prec, scale in rows])


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def extract_table(
    conn: psycopg.Connection,
    table: Table,
    state: dict,
    started_at: datetime,
    run_id: str,
    out_dir: Path,
) -> int:
    schema = table_schema(conn, table.name)
    cols = ", ".join(schema.names)

    if table.mode == "updated_at":
        last = datetime.fromisoformat(state[table.name]) if table.name in state else EPOCH
        sql = (
            f"SELECT {cols} FROM {table.name} "
            f"WHERE updated_at > %s AND updated_at <= %s ORDER BY updated_at, {table.pk}"
        )
        params = (last, started_at)
        new_mark = started_at.isoformat()
    else:
        last_id = state.get(table.name, 0)
        sql = f"SELECT {cols} FROM {table.name} WHERE {table.pk} > %s ORDER BY {table.pk}"
        params = (last_id,)
        new_mark = None

    rows = conn.execute(sql, params).fetchall()

    if rows:
        arrays = [pa.array([r[i] for r in rows], type=f.type) for i, f in enumerate(schema)]
        data = pa.Table.from_arrays(arrays, schema=schema)
        data = data.append_column("_extracted_at", pa.array([started_at] * len(rows), type=TS_UTC))
        data = data.append_column("_batch_id", pa.array([run_id] * len(rows), type=pa.string()))

        day = started_at.astimezone(timezone.utc).date().isoformat()
        dest = out_dir / "erp" / table.name / f"ingestion_date={day}"
        dest.mkdir(parents=True, exist_ok=True)
        final = dest / f"{table.name}_{run_id}.parquet"
        tmp = final.with_name(final.name + ".tmp")
        pq.write_table(data, tmp, compression="snappy")
        tmp.replace(final)

        if table.mode == "id":
            new_mark = rows[-1][schema.names.index(table.pk)]

    if new_mark is not None:
        state[table.name] = new_mark
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract ERP tables to Parquet (bronze).")
    parser.add_argument("--out", default=os.getenv("BRONZE_DIR", "./out/bronze"))
    parser.add_argument("--full-refresh", action="store_true", help="ignore saved watermarks")
    args = parser.parse_args()

    out_dir = Path(args.out)
    state_path = out_dir / "_state" / "watermarks.json"
    state = {} if args.full_refresh else load_state(state_path)

    with connect() as conn:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        conn.read_only = True
        started_at = conn.execute("SELECT now()").fetchone()[0]
        run_id = started_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        print(f"run {run_id} -> {out_dir}")

        for table in TABLES:
            count = extract_table(conn, table, state, started_at, run_id, out_dir)
            save_state(state_path, state)
            print(f"  {table.name}: {count} rows")


if __name__ == "__main__":
    main()
