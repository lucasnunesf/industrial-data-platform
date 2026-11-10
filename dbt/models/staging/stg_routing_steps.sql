select
    routing_step_id,
    routing_id,
    step_sequence,
    work_center_id
from {{ source('silver', 'silver_routing_steps') }}
