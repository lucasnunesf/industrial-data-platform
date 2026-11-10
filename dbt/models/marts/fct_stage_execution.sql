with stage_runs as (
    select
        production_order_id,
        routing_step_id,
        min(case when event_type = 'start' then event_ts end) as started_at,
        max(case when event_type = 'finish' then event_ts end) as finished_at,
        max(machine_id) as machine_id,
        sum(good_quantity) as good_quantity,
        sum(scrap_quantity) as scrap_quantity
    from {{ ref('stg_production_stage_events') }}
    group by production_order_id, routing_step_id
),

enriched as (
    select
        s.production_order_id,
        s.routing_step_id,
        rs.step_sequence,
        rs.work_center_id,
        s.machine_id,
        po.sales_order_item_id,
        soi.sales_order_id,
        soi.product_id,
        so.customer_id,
        s.started_at,
        s.finished_at,
        s.good_quantity,
        s.scrap_quantity
    from stage_runs as s
    inner join {{ ref('stg_routing_steps') }} as rs on rs.routing_step_id = s.routing_step_id
    inner join {{ ref('stg_production_orders') }} as po on po.production_order_id = s.production_order_id
    inner join {{ ref('stg_sales_order_items') }} as soi on soi.sales_order_item_id = po.sales_order_item_id
    inner join {{ ref('stg_sales_orders') }} as so on so.sales_order_id = soi.sales_order_id
)

select
    production_order_id,
    routing_step_id,
    step_sequence,
    work_center_id,
    machine_id,
    sales_order_id,
    product_id,
    customer_id,
    started_at,
    finished_at,
    datediff(minute, started_at, finished_at) as duration_minutes,
    datediff(
        minute,
        lag(finished_at) over (partition by production_order_id order by step_sequence),
        started_at
    ) as wait_minutes,
    good_quantity,
    scrap_quantity
from enriched
