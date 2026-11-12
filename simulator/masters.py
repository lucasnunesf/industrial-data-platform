"""Variable master data: materials, customers, products, operators, exchange rates."""

import csv
import random
from datetime import date
from pathlib import Path

from faker import Faker

import factory_config as cfg
from db import lookup

PTAX_FILE = Path(__file__).parent / "data" / "ptax_usd_brl.csv"


def load_materials(conn) -> None:
    conn.cursor().executemany(
        """INSERT INTO materials (material_code, material_name, material_thickness_mm,
                                  material_density_g_cm3, material_price_usd_per_kg)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (material_code) DO NOTHING""",
        [(*m[:4], m[5]) for m in cfg.MATERIALS],
    )


def load_customers(conn) -> None:
    fake = Faker("pt_BR")
    fake.seed_instance(cfg.SEED)
    rows = []
    for i in range(1, cfg.N_CUSTOMERS + 1):
        cnpj = "".join(ch for ch in fake.cnpj() if ch.isdigit())
        rows.append((f"Company {i:03d}", cnpj, fake.city(), fake.estado_sigla()))
    conn.cursor().executemany(
        """INSERT INTO customers (company_name, cnpj, city, state)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (cnpj) DO NOTHING""",
        rows,
    )


def load_products(conn) -> None:
    rng = random.Random(cfg.SEED)
    materials = lookup(conn, "materials", "material_code", "material_id")
    routings = lookup(conn, "routings", "routing_code", "routing_id")
    routing_codes = list(cfg.ROUTING_WEIGHTS)
    rows = []
    for i in range(1, cfg.N_PRODUCTS + 1):
        material = rng.choice(cfg.MATERIALS)
        routing = rng.choices(routing_codes, weights=cfg.ROUTING_WEIGHTS.values())[0]
        part = rng.choice(cfg.PART_TYPES)
        weight = round(rng.uniform(0.3, 25.0), 3)
        rows.append((f"P-{i:04d}", f"{part} {material[1].split()[-1]} {material[0].split('-')[0]}",
                     materials[material[0]], routings[routing], weight))
    conn.cursor().executemany(
        """INSERT INTO products (product_code, product_name, material_id,
                                 routing_id, product_unit_weight_kg)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (product_code) DO NOTHING""",
        rows,
    )


def load_operators(conn) -> None:
    if conn.execute("SELECT count(*) FROM operators").fetchone()[0] > 0:
        return
    fake = Faker("pt_BR")
    fake.seed_instance(cfg.SEED)
    centers = lookup(conn, "work_centers", "work_center_code", "work_center_id")
    rows = [
        (fake.name(), centers[wc], role)
        for wc, role, n in cfg.OPERATORS
        for _ in range(n)
    ]
    conn.cursor().executemany(
        "INSERT INTO operators (operator_name, work_center_id, operator_role) VALUES (%s, %s, %s)",
        rows,
    )


def load_exchange_rates(conn, until: date) -> None:
    """Load the PTAX rates published up to the cut-off date, like a daily import job."""
    with PTAX_FILE.open(encoding="utf-8") as f:
        rows = [
            ("USD", r["rate_date"], r["buy_rate"], r["sell_rate"])
            for r in csv.DictReader(f)
            if date.fromisoformat(r["rate_date"]) <= until
        ]
    conn.cursor().executemany(
        """INSERT INTO exchange_rates (currency_code, rate_date, buy_rate_brl, sell_rate_brl)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (currency_code, rate_date) DO NOTHING""",
        rows,
    )


def load_all(conn, until: date) -> None:
    load_materials(conn)
    load_customers(conn)
    load_products(conn)
    load_operators(conn)
    load_exchange_rates(conn, until)
