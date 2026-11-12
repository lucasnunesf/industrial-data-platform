-- Scrapped material is part of the material bought for the order, never more than it.
select
    sales_order_id,
    scrap_material_cost_brl,
    material_cost_brl
from {{ ref('fct_order_margin') }}
where scrap_material_cost_brl > material_cost_brl
