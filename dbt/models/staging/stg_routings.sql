select
    routing_id,
    routing_code,
    routing_name
from {{ source('silver', 'silver_routings') }}
