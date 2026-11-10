select
    work_center_id,
    work_center_code,
    work_center_name
from {{ source('silver', 'silver_work_centers') }}
