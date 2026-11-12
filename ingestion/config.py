from dataclasses import dataclass


@dataclass(frozen=True)
class Table:
    name: str
    cursor_column: str  # time column used as the watermark
    pk: str


# Bronze folder of this source. The suffix is bumped when the ERP schema changes in a way that
# old files cannot follow (v2: cost, freight and exchange rate columns), so versions never mix.
SOURCE_FOLDER = "erp_v2"

TABLES = [
    Table("customers", "updated_at", "customer_id"),
    Table("materials", "updated_at", "material_id"),
    Table("work_centers", "updated_at", "work_center_id"),
    Table("machines", "updated_at", "machine_id"),
    Table("operators", "updated_at", "operator_id"),
    Table("routings", "updated_at", "routing_id"),
    Table("routing_steps", "updated_at", "routing_step_id"),
    Table("products", "updated_at", "product_id"),
    Table("sales_orders", "updated_at", "sales_order_id"),
    Table("sales_order_items", "updated_at", "sales_order_item_id"),
    Table("production_orders", "updated_at", "production_order_id"),
    Table("shipments", "updated_at", "shipment_id"),
    Table("exchange_rates", "updated_at", "exchange_rate_id"),
    Table("production_stage_events", "created_at", "event_id"),
    Table("quality_inspections", "created_at", "inspection_id"),
]
