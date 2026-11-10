select
    sales_order_item_id,
    sales_order_id,
    line_number,
    product_id,
    quantity,
    unit_price_brl
from {{ source('silver', 'silver_sales_order_items') }}
