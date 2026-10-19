-- One clean row per account: trimmed and lowercased categories, real types,
-- out-of-range optional values set to NULL, rows missing required fields removed
with typed as (
    select
        upper(trim(account_id))                 as account_id,
        trim(name)                              as name,
        lower(trim(industry))                   as industry,
        try_cast(employee_count as integer)     as employee_count,
        try_cast(annual_revenue_musd as double) as annual_revenue_musd,
        lower(trim(region))                     as region,
        lower(trim(funding_stage))              as funding_stage,
        try_cast(growth_rate_yoy as double)     as growth_rate_yoy,
        try_cast(hiring_velocity as double)     as hiring_velocity,
        try_cast(tech_stack_score as double)    as tech_stack_score,
        try_cast(founded_year as integer)       as founded_year
    from {{ source('raw', 'accounts') }}
),

ranged as (
    select
        account_id, name, industry, employee_count,
        case when annual_revenue_musd >= 0 then annual_revenue_musd end         as annual_revenue_musd,
        region, funding_stage,
        case when growth_rate_yoy between -1 and 2 then growth_rate_yoy end     as growth_rate_yoy,
        case when hiring_velocity between 0 and 1 then hiring_velocity end      as hiring_velocity,
        tech_stack_score, founded_year
    from typed
),

valid as (
    -- No ORDER BY inside the window: DuckDB 1.5 crashes on PARTITION BY x ORDER BY x
    select *, row_number() over (partition by account_id) as rn
    from ranged
    where account_id is not null
      and industry in ({{ sql_list(var('industries')) }})
      and region in ({{ sql_list(var('regions')) }})
      and funding_stage in ({{ sql_list(var('funding_stages')) }})
      and employee_count > 0
      and tech_stack_score between 0 and 1
      and founded_year between 1900 and year(current_date)
)

select * exclude (rn) from valid where rn = 1
