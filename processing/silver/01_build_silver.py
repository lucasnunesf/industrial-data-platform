# Fabric notebook: bronze (Parquet via shortcut) -> silver (Delta tables in the Lakehouse).
# Attach the lakehouse lh_industrial as the default lakehouse before running.

# %% [markdown]
# Bronze is append-only, so a row updated twice appears in two files.
# Silver keeps the latest version of each primary key and registers one Delta table per source table.

# %%
from pyspark.sql import Window
from pyspark.sql import functions as F

BRONZE_PATH = "Files/erp"

# table -> (primary key, columns that define "latest version", newest first)
TABLES = {
    "customers": ("customer_id", ["updated_at", "_extracted_at"]),
    "materials": ("material_id", ["updated_at", "_extracted_at"]),
    "work_centers": ("work_center_id", ["updated_at", "_extracted_at"]),
    "machines": ("machine_id", ["updated_at", "_extracted_at"]),
    "operators": ("operator_id", ["updated_at", "_extracted_at"]),
    "routings": ("routing_id", ["updated_at", "_extracted_at"]),
    "routing_steps": ("routing_step_id", ["updated_at", "_extracted_at"]),
    "products": ("product_id", ["updated_at", "_extracted_at"]),
    "sales_orders": ("sales_order_id", ["updated_at", "_extracted_at"]),
    "sales_order_items": ("sales_order_item_id", ["updated_at", "_extracted_at"]),
    "production_orders": ("production_order_id", ["updated_at", "_extracted_at"]),
    "shipments": ("shipment_id", ["updated_at", "_extracted_at"]),
    "production_stage_events": ("event_id", ["_extracted_at"]),
    "quality_inspections": ("inspection_id", ["_extracted_at"]),
}


# %%
def build_silver(table: str, pk: str, order_cols: list[str]) -> int:
    bronze = spark.read.parquet(f"{BRONZE_PATH}/{table}")
    latest = Window.partitionBy(pk).orderBy(*[F.col(c).desc() for c in order_cols])
    silver = (
        bronze.withColumn("_rn", F.row_number().over(latest))
        .filter("_rn = 1")
        .drop("_rn")
        .withColumn("_silver_loaded_at", F.current_timestamp())
    )
    (
        silver.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(f"silver_{table}")
    )
    return silver.count()


# %%
for table, (pk, order_cols) in TABLES.items():
    rows = build_silver(table, pk, order_cols)
    print(f"silver_{table}: {rows} rows")
