select
    material_id,
    material_code,
    material_name,
    material_thickness_mm,
    material_density_g_cm3,
    material_price_usd_per_kg
from {{ source('silver', 'silver_materials') }}
