"""Variable master data: materials, customers, products, operators."""

import random

from faker import Faker

import factory_config as cfg
from db import lookup


def load_materials(conn) -> None:
    conn.cursor().executemany(
        """INSERT INTO materials (material_code, material_name,
                                  material_thickness_mm, material_density_g_cm3)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (material_code) DO NOTHING""",
        [m[:4] for m in cfg.MATERIALS],
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


def load_all(conn) -> None:
    load_materials(conn)
    load_customers(conn)
    load_products(conn)
    load_operators(conn)
