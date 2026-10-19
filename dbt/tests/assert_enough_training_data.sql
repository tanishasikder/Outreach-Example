-- The model needs enough closed deals, and both outcomes (won and lost), to learn anything.
-- Returns a row (= test fails) if not.
with closed as (
    select status from {{ ref('deal_training') }} where status in ('won', 'lost')
)

select count(*) as closed_deals, count(distinct status) as outcomes
from closed
having count(*) < {{ var('min_training_rows') }}
    or count(distinct status) < 2
