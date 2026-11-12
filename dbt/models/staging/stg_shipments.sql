select
    shipment_id,
    shipment_number,
    sales_order_id,
    shipped_at,
    delivered_at,
    shipment_status,
    freight_cost_brl
from {{ source('silver', 'silver_shipments') }}
