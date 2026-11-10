select
    machine_id,
    machine_code,
    machine_name,
    work_center_id
from {{ ref('stg_machines') }}
