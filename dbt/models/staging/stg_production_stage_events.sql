select
    event_id,
    production_order_id,
    routing_step_id,
    event_type,
    event_ts,
    machine_id,
    operator_id,
    good_quantity,
    scrap_quantity,
    work_minutes
from {{ source('silver', 'silver_production_stage_events') }}
