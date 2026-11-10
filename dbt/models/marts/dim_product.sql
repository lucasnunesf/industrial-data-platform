select
    p.product_id,
    p.product_code,
    p.product_name,
    m.material_name,
    m.material_thickness_mm,
    p.product_unit_weight_kg,
    r.routing_name
from {{ ref('stg_products') }} as p
inner join {{ ref('stg_materials') }} as m on m.material_id = p.material_id
inner join {{ ref('stg_routings') }} as r on r.routing_id = p.routing_id
