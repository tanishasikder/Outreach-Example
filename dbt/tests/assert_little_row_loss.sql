-- Cleaning should only remove a few bad rows. If it removes more than max_row_loss of any
-- table, the raw export is probably broken (wrong columns, new spellings...), so stop here
-- instead of training a model on a fraction of the data. Returns the failing tables.
with counts as (
    select 'accounts' as table_name,
           (select count(*) from {{ source('raw', 'accounts') }}) as raw_rows,
           (select count(*) from {{ ref('stg_accounts') }})       as clean_rows
    union all
    select 'deals',
           (select count(*) from {{ source('raw', 'deals') }}),
           (select count(*) from {{ ref('stg_deals') }})
    union all
    select 'events',
           (select count(*) from {{ source('raw', 'events') }}),
           (select count(*) from {{ ref('stg_events') }})
)

select *, 1 - clean_rows / raw_rows as share_removed
from counts
where raw_rows = 0
   or clean_rows < raw_rows * (1 - {{ var('max_row_loss') }})
