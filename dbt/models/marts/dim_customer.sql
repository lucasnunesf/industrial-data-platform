select
    customer_id,
    company_name,
    city,
    state
from {{ ref('stg_customers') }}
