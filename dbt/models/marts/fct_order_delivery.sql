with order_value as (
    select
        sales_order_id,
        sum(quantity * unit_price_brl) as order_value_brl
    from {{ ref('stg_sales_order_items') }}
    group by sales_order_id
),

shipment as (
    select
        sales_order_id,
        min(shipped_at) as shipped_at,
        max(delivered_at) as delivered_at,
        max(shipment_status) as shipment_status
    from {{ ref('stg_shipments') }}
    group by sales_order_id
)

select
    so.sales_order_id,
    so.sales_order_number,
    so.customer_id,
    so.order_date,
    so.promised_date,
    so.sales_order_status,
    ov.order_value_brl,
    sh.shipped_at,
    sh.delivered_at,
    sh.shipment_status,
    datediff(day, so.order_date, cast(sh.delivered_at as date)) as lead_time_days,
    datediff(day, so.promised_date, cast(sh.delivered_at as date)) as days_late,
    case
        when sh.delivered_at is null then null
        when cast(sh.delivered_at as date) <= so.promised_date then 1
        else 0
    end as is_on_time
from {{ ref('stg_sales_orders') }} as so
left join order_value as ov on ov.sales_order_id = so.sales_order_id
left join shipment as sh on sh.sales_order_id = so.sales_order_id
