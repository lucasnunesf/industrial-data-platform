select
    work_center_id,
    work_center_code,
    work_center_name
from {{ ref('stg_work_centers') }}
