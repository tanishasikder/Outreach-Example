-- Engagement events with exact duplicates removed and unknown accounts dropped
select distinct
    upper(trim(account_id))         as account_id,
    try_cast(event_date as date)    as event_date,
    lower(trim(event_type))         as event_type
from {{ source('raw', 'events') }}
where try_cast(event_date as date) is not null
  and lower(trim(event_type)) in ({{ sql_list(var('event_types')) }})
  and upper(trim(account_id)) in (select account_id from {{ ref('stg_accounts') }})
