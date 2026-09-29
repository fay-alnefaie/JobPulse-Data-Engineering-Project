-- Checks that the number of rows in int_jobs_preferred_source matches
-- the number of distinct (job_title, company_name, normalized_city_name)
-- combinations in int_jobs_final 
-- i.e. dedup kept exactly one row
-- per group, no more and no less.
with expected as (

    select count(*) as expected_rows
    from (
        select
            trim(lower(job_title)) as job_title,
            trim(lower(company_name)) as company_name,
            normalized_city_name
        from {{ ref('int_jobs_final') }}
        group by 1, 2, 3
    )

),

actual as (

    select count(*) as actual_rows
    from {{ ref('int_jobs_preferred_source') }}

)

select
    expected.expected_rows,
    actual.actual_rows
from expected
cross join actual
where expected.expected_rows <> actual.actual_rows