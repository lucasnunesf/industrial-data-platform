select
    customer_id,
    company_name,
    cnpj,
    city,
    state
from {{ source('silver', 'silver_customers') }}
