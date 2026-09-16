-- models/intermediate/int_jobs_country.sql
-- Business/data interpretation:
-- Keep Saudi Arabia jobs only. Runs right after location normalization
-- because it depends on normalized_country_name.

with source as (

    select *
    from {{ ref('int_jobs_location') }}

),

filtered as (

    select *
    from source
    where normalized_country_name = 'Saudi Arabia'

)

select *
from filtered
