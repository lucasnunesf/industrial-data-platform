select
    product_id,
    product_code,
    product_name,
    material_id,
    routing_id,
    product_unit_weight_kg
from {{ source('silver', 'silver_products') }}
