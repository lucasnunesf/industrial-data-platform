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
        max(shipment_status) as shipment_status,
        sum(freight_cost_brl) as freight_cost_brl
    from {{ ref('stg_shipments') }}
    group by sales_order_id
),

-- Reference date: the last day with orders in the ERP, so the result does not depend on the clock.
as_of as (
    select max(order_date) as as_of_date
    from {{ ref('stg_sales_orders') }}
),

orders as (
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
        sh.freight_cost_brl,
        a.as_of_date,
        case
            when sh.delivered_at is null
                and so.promised_date < a.as_of_date
                and so.sales_order_status <> 'cancelled' then 1
            else 0
        end as is_overdue
    from {{ ref('stg_sales_orders') }} as so
    cross join as_of as a
    left join order_value as ov on ov.sales_order_id = so.sales_order_id
    left join shipment as sh on sh.sales_order_id = so.sales_order_id
)

select
    sales_order_id,
    sales_order_number,
    customer_id,
    order_date,
    promised_date,
    sales_order_status,
    order_value_brl,
    shipped_at,
    delivered_at,
    shipment_status,
    freight_cost_brl,
    is_overdue,
    datediff(day, order_date, cast(delivered_at as date)) as lead_time_days,
    case
        when delivered_at is not null then datediff(day, promised_date, cast(delivered_at as date))
        when is_overdue = 1 then datediff(day, promised_date, as_of_date)
    end as days_late,
    case
        when delivered_at is not null and cast(delivered_at as date) <= promised_date then 1
        when delivered_at is not null then 0
        when is_overdue = 1 then 0
    end as is_on_time
from orders
