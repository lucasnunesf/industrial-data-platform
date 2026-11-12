-- Working time can never be longer than the wall-clock time between start and finish.
select
    production_order_id,
    routing_step_id,
    work_minutes,
    duration_minutes
from {{ ref('fct_stage_execution') }}
where finished_at is not null
    and work_minutes > duration_minutes + 1
