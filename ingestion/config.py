from dataclasses import dataclass


@dataclass(frozen=True)
class Table:
    name: str
    mode: str  # "updated_at": mutable rows; "id": append-only rows
    pk: str


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
    Table("production_stage_events", "id", "event_id"),
    Table("quality_inspections", "id", "inspection_id"),
]
