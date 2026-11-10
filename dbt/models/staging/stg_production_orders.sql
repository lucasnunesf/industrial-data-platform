select
    production_order_id,
    production_order_number,
    sales_order_item_id,
    planned_quantity,
    planned_start_date,
    due_date,
    production_order_status
from {{ source('silver', 'silver_production_orders') }}
