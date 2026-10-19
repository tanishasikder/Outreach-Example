-- One row per deal with the answer (status) and the columns the model learns from.
-- The feature columns are exactly the fields the API accepts (src/schemas/validate.py),
-- so the model is only trained on information a user can type into the form
select
    d.deal_id,
    d.created_date,
    d.status,
    -- Deal fields
    d.amount,
    d.lead_source,
    -- Company fields
    a.industry,
    a.employee_count,
    a.region,
    a.funding_stage,
    a.tech_stack_score,
    a.founded_year,
    a.annual_revenue_musd,
    a.growth_rate_yoy,
    a.hiring_velocity
from {{ ref('stg_deals') }} as d
join {{ ref('stg_accounts') }} as a using (account_id)
