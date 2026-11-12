# Fabric notebook: data quality checks on the silver tables. Fails if any check fails.
# Run it after 01_build_silver, with lh_industrial as the default lakehouse.

# %% [markdown]
# Checks: dedup against bronze, primary key unique and not null, foreign keys, accepted values,
# and amounts that can never be negative.

# %%
from pyspark.sql import functions as F

BRONZE_PATH = "Files/erp"

PRIMARY_KEYS = {
    "customers": "customer_id",
    "materials": "material_id",
    "work_centers": "work_center_id",
    "machines": "machine_id",
    "operators": "operator_id",
    "routings": "routing_id",
    "routing_steps": "routing_step_id",
    "products": "product_id",
    "sales_orders": "sales_order_id",
    "sales_order_items": "sales_order_item_id",
    "production_orders": "production_order_id",
    "shipments": "shipment_id",
    "exchange_rates": "exchange_rate_id",
    "production_stage_events": "event_id",
    "quality_inspections": "inspection_id",
}

# (child table, child column, parent table)
FOREIGN_KEYS = [
    ("machines", "work_center_id", "work_centers"),
    ("operators", "work_center_id", "work_centers"),
    ("routing_steps", "routing_id", "routings"),
    ("routing_steps", "work_center_id", "work_centers"),
    ("products", "material_id", "materials"),
    ("products", "routing_id", "routings"),
    ("sales_orders", "customer_id", "customers"),
    ("sales_order_items", "sales_order_id", "sales_orders"),
    ("sales_order_items", "product_id", "products"),
    ("production_orders", "sales_order_item_id", "sales_order_items"),
    ("production_stage_events", "production_order_id", "production_orders"),
    ("production_stage_events", "routing_step_id", "routing_steps"),
    ("production_stage_events", "machine_id", "machines"),
    ("production_stage_events", "operator_id", "operators"),
    ("quality_inspections", "production_order_id", "production_orders"),
    ("quality_inspections", "inspector_id", "operators"),
    ("shipments", "sales_order_id", "sales_orders"),
]

# (table, column, allowed values)
ACCEPTED_VALUES = [
    ("sales_orders", "sales_order_status", ["open", "in_production", "shipped", "cancelled"]),
    ("production_orders", "production_order_status", ["planned", "released", "in_progress", "completed", "cancelled"]),
    ("production_stage_events", "event_type", ["start", "finish"]),
    ("quality_inspections", "inspection_result", ["approved", "rejected", "rework"]),
    ("shipments", "shipment_status", ["shipped", "delivered", "returned"]),
    ("operators", "operator_role", ["machine_operator", "unloader", "welder", "assembler", "finisher", "inspector"]),
]

# (table, column): prices, rates, costs and times that can never be negative
NON_NEGATIVE = [
    ("materials", "material_price_usd_per_kg"),
    ("work_centers", "hourly_rate_brl"),
    ("production_stage_events", "work_minutes"),
    ("shipments", "freight_cost_brl"),
    ("exchange_rates", "sell_rate_brl"),
]

results = []


def record(check: str, table: str, bad_rows: int) -> None:
    results.append((check, table, bad_rows, "PASS" if bad_rows == 0 else "FAIL"))


# %%
for table, pk in PRIMARY_KEYS.items():
    silver = spark.table(f"silver_{table}")
    bronze_keys = spark.read.parquet(f"{BRONZE_PATH}/{table}").select(pk).distinct().count()

    record("not_empty", table, 1 if silver.count() == 0 else 0)
    record("matches_distinct_bronze_keys", table, abs(silver.count() - bronze_keys))
    record("pk_not_null", table, silver.filter(F.col(pk).isNull()).count())
    record("pk_unique", table, silver.count() - silver.select(pk).distinct().count())

# %%
for child, column, parent in FOREIGN_KEYS:
    parent_pk = PRIMARY_KEYS[parent]
    orphans = (
        spark.table(f"silver_{child}")
        .filter(F.col(column).isNotNull())
        .join(
            spark.table(f"silver_{parent}").select(F.col(parent_pk).alias(column)),
            on=column,
            how="left_anti",
        )
        .count()
    )
    record(f"fk_{column}_in_{parent}", child, orphans)

# %%
for table, column, allowed in ACCEPTED_VALUES:
    invalid = spark.table(f"silver_{table}").filter(~F.col(column).isin(allowed)).count()
    record(f"accepted_values_{column}", table, invalid)

# %%
for table, column in NON_NEGATIVE:
    negative = spark.table(f"silver_{table}").filter(F.col(column) < 0).count()
    record(f"non_negative_{column}", table, negative)

# %%
report = spark.createDataFrame(results, ["check", "table", "bad_rows", "status"])
report.orderBy(F.col("status"), "table", "check").show(200, truncate=False)

failed = [r for r in results if r[3] == "FAIL"]
print(f"{len(results) - len(failed)} passed, {len(failed)} failed")
assert not failed, f"{len(failed)} silver checks failed"
