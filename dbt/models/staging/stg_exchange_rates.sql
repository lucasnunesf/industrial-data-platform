select
    exchange_rate_id,
    currency_code,
    rate_date,
    buy_rate_brl,
    sell_rate_brl
from {{ source('silver', 'silver_exchange_rates') }}
