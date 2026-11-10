select
    production_order_id,
    routing_step_id
from {{ ref('fct_stage_execution') }}
where finished_at < started_at
