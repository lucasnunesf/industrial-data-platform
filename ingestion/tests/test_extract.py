from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pyarrow.parquet as pq
import pytest

import extract
from config import TABLES

TABLE = {t.name: t for t in TABLES}


def run_extraction(params: dict, table_name: str, state: dict, out_dir: Path) -> list[dict]:
    """Run one extraction of a table the way main() does and return the rows it wrote."""
    with psycopg.connect(**params) as conn:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        conn.read_only = True
        started_at = conn.execute("SELECT now()").fetchone()[0]
        extract.extract_table(conn, TABLE[table_name], state, started_at, "test", out_dir)
    files = sorted((out_dir / "erp" / table_name).rglob("*.parquet"))
    return [row for f in files for row in pq.read_table(f).to_pylist()]


def make_production_order(conn: psycopg.Connection) -> tuple[int, int]:
    """Insert the chain of rows a production event depends on."""
    customer = conn.execute(
        "INSERT INTO customers (company_name, cnpj, city, state) "
        "VALUES ('Company 001', '00000000000100', 'Sorocaba', 'SP') RETURNING customer_id"
    ).fetchone()[0]
    material = conn.execute(
        "INSERT INTO materials (material_code, material_name, material_thickness_mm, material_density_g_cm3) "
        "VALUES ('CS-3', 'Carbon steel 3 mm', 3, 7.85) RETURNING material_id"
    ).fetchone()[0]
    routing, step = conn.execute(
        "SELECT routing_id, routing_step_id FROM routing_steps ORDER BY routing_id, step_sequence LIMIT 1"
    ).fetchone()
    product = conn.execute(
        "INSERT INTO products (product_code, product_name, material_id, routing_id, product_unit_weight_kg) "
        "VALUES ('P-001', 'Panel', %s, %s, 1.5) RETURNING product_id",
        (material, routing),
    ).fetchone()[0]
    order = conn.execute(
        "INSERT INTO sales_orders (sales_order_number, customer_id, order_date, promised_date) "
        "VALUES ('SO-1', %s, '2026-07-01', '2026-07-10') RETURNING sales_order_id",
        (customer,),
    ).fetchone()[0]
    item = conn.execute(
        "INSERT INTO sales_order_items (sales_order_id, line_number, product_id, quantity, unit_price_brl) "
        "VALUES (%s, 1, %s, 10, 100) RETURNING sales_order_item_id",
        (order, product),
    ).fetchone()[0]
    production_order = conn.execute(
        "INSERT INTO production_orders (production_order_number, sales_order_item_id, planned_quantity, "
        "planned_start_date, due_date) VALUES ('PO-1', %s, 10, '2026-07-01', '2026-07-10') "
        "RETURNING production_order_id",
        (item,),
    ).fetchone()[0]
    return production_order, step


def test_update_committed_after_an_extraction_is_not_lost(erp_db, tmp_path):
    state = {}
    with psycopg.connect(autocommit=True, **erp_db) as conn:
        conn.execute(
            "INSERT INTO customers (company_name, cnpj, city, state) "
            "VALUES ('Company 001', '00000000000100', 'Sorocaba', 'SP')"
        )
    first = run_extraction(erp_db, "customers", state, tmp_path / "run1")
    assert [r["city"] for r in first] == ["Sorocaba"]

    # The update gets updated_at = start of its transaction, but commits only after the next extraction.
    with psycopg.connect(**erp_db) as writer:
        writer.execute("UPDATE customers SET city = 'Lisbon'")
        run_extraction(erp_db, "customers", state, tmp_path / "run2")
        writer.commit()

    after = run_extraction(erp_db, "customers", state, tmp_path / "run3")
    assert "Lisbon" in [r["city"] for r in after]


def test_event_committed_out_of_order_is_not_lost(erp_db, tmp_path):
    with psycopg.connect(autocommit=True, **erp_db) as conn:
        production_order, step = make_production_order(conn)
    insert = (
        "INSERT INTO production_stage_events (production_order_id, routing_step_id, event_type, event_ts) "
        "VALUES (%s, %s, %s, now()) RETURNING event_id"
    )
    state = {}

    # Two writers: the slow one takes the lower event_id but commits after the fast one.
    with psycopg.connect(**erp_db) as slow, psycopg.connect(autocommit=True, **erp_db) as fast:
        slow_id = slow.execute(insert, (production_order, step, "start")).fetchone()[0]
        fast.execute(insert, (production_order, step, "finish"))
        run_extraction(erp_db, "production_stage_events", state, tmp_path / "run1")
        slow.commit()

    after = run_extraction(erp_db, "production_stage_events", state, tmp_path / "run2")
    assert slow_id in [r["event_id"] for r in after]


def test_run_ids_within_the_same_second_are_unique():
    started_at = datetime(2026, 11, 12, 10, 0, 0, 100, tzinfo=timezone.utc)
    assert extract.make_run_id(started_at) != extract.make_run_id(started_at + timedelta(microseconds=1))


def test_a_file_from_another_run_is_never_overwritten(erp_db, tmp_path):
    with psycopg.connect(autocommit=True, **erp_db) as conn:
        conn.execute(
            "INSERT INTO customers (company_name, cnpj, city, state) "
            "VALUES ('Company 001', '00000000000100', 'Sorocaba', 'SP')"
        )
        started_at = conn.execute("SELECT now()").fetchone()[0]
        extract.extract_table(conn, TABLE["customers"], {}, started_at, "same-run", tmp_path)
        with pytest.raises(FileExistsError):
            extract.extract_table(conn, TABLE["customers"], {}, started_at, "same-run", tmp_path)
