-- One row per shipped sales order: its costs are final only after the order has left the plant.
with order_total as (
    select
        soi.sales_order_id,
        sum(soi.quantity * soi.unit_price_brl) as revenue_brl,
        sum(soi.quantity * p.product_unit_weight_kg * m.material_price_usd_per_kg) as material_cost_usd
    from {{ ref('stg_sales_order_items') }} as soi
    inner join {{ ref('stg_products') }} as p on p.product_id = soi.product_id
    inner join {{ ref('stg_materials') }} as m on m.material_id = p.material_id
    group by soi.sales_order_id
),

stage as (
    select
        se.sales_order_id,
        sum(se.stage_cost_brl) as processing_cost_brl,
        sum(se.scrap_quantity * p.product_unit_weight_kg * m.material_price_usd_per_kg) as scrap_material_cost_usd
    from {{ ref('fct_stage_execution') }} as se
    inner join {{ ref('stg_products') }} as p on p.product_id = se.product_id
    inner join {{ ref('stg_materials') }} as m on m.material_id = p.material_id
    group by se.sales_order_id
),

shipment as (
    select
        sales_order_id,
        sum(freight_cost_brl) as freight_cost_brl
    from {{ ref('stg_shipments') }}
    group by sales_order_id
),

-- PTAX exists for business days only: use the latest rate on or before the order date.
rate_date as (
    select
        so.sales_order_id,
        max(er.rate_date) as rate_date
    from {{ ref('stg_sales_orders') }} as so
    inner join {{ ref('stg_exchange_rates') }} as er
        on er.currency_code = 'USD' and er.rate_date <= so.order_date
    group by so.sales_order_id
),

costed as (
    select
        so.sales_order_id,
        so.sales_order_number,
        so.customer_id,
        so.order_date,
        er.sell_rate_brl as usd_brl_rate,
        ot.revenue_brl,
        cast(ot.material_cost_usd * er.sell_rate_brl as decimal(18, 2)) as material_cost_brl,
        cast(st.scrap_material_cost_usd * er.sell_rate_brl as decimal(18, 2)) as scrap_material_cost_brl,
        st.processing_cost_brl,
        sh.freight_cost_brl
    from {{ ref('stg_sales_orders') }} as so
    inner join order_total as ot on ot.sales_order_id = so.sales_order_id
    inner join stage as st on st.sales_order_id = so.sales_order_id
    inner join shipment as sh on sh.sales_order_id = so.sales_order_id
    inner join rate_date as rd on rd.sales_order_id = so.sales_order_id
    inner join {{ ref('stg_exchange_rates') }} as er
        on er.currency_code = 'USD' and er.rate_date = rd.rate_date
    where so.sales_order_status = 'shipped'
)

select
    sales_order_id,
    sales_order_number,
    customer_id,
    order_date,
    usd_brl_rate,
    revenue_brl,
    material_cost_brl,
    scrap_material_cost_brl,
    processing_cost_brl,
    freight_cost_brl,
    revenue_brl - material_cost_brl - processing_cost_brl - freight_cost_brl as margin_brl
from costed
