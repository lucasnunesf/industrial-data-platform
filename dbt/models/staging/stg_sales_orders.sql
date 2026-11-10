select
    sales_order_id,
    sales_order_number,
    customer_id,
    order_date,
    promised_date,
    sales_order_status
from {{ source('silver', 'silver_sales_orders') }}
