select
    production_order_id,
    routing_step_id,
    count(*) as rows_found
from {{ ref('fct_stage_execution') }}
group by production_order_id, routing_step_id
having count(*) > 1
