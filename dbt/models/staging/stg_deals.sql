-- One clean row per deal. Open deals have no close date; closed deals must close after they start
with typed as (
    select
        upper(trim(deal_id))            as deal_id,
        upper(trim(account_id))         as account_id,
        try_cast(created_date as date)  as created_date,
        try_cast(close_date as date)    as close_date,
        lower(trim(status))             as status,
        try_cast(amount as double)      as amount,
        lower(trim(lead_source))        as lead_source
    from {{ source('raw', 'deals') }}
),

valid as (
    select
        deal_id, account_id, created_date,
        case when status = 'open' then null else close_date end as close_date,
        status, amount, lead_source,
        row_number() over (partition by deal_id order by created_date) as rn
    from typed
    where deal_id is not null
      and account_id in (select account_id from {{ ref('stg_accounts') }})
      and status in ({{ sql_list(var('statuses')) }})
      and lead_source in ({{ sql_list(var('lead_sources')) }})
      and amount > 0
      and created_date is not null
      and (status = 'open' or close_date >= created_date)
)

select * exclude (rn) from valid where rn = 1
