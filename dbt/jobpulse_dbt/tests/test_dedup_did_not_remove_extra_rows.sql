-- Verify that deduplication removed only duplicate rows.
-- Expected rows = unique (source_job_id, job_url) combinations.
-- Test passes when actual rows match expected rows.

with before_dedup as (

    select count(*) as before_rows
    from {{ ref('stg_jobs') }}

),

expected_after_dedup as (

    select count(*) as expected_rows
    from (
        select
            source_job_id,
            job_url
        from {{ ref('stg_jobs') }}
        group by
            source_job_id,
            job_url
    )

),

actual_after_dedup as (

    select count(*) as actual_rows
    from {{ ref('int_jobs_city_deduped') }}

)

select
    before_dedup.before_rows,
    expected_after_dedup.expected_rows,
    actual_after_dedup.actual_rows,
    before_dedup.before_rows - expected_after_dedup.expected_rows
        as expected_removed_rows,
    before_dedup.before_rows - actual_after_dedup.actual_rows
        as actual_removed_rows

from before_dedup
cross join expected_after_dedup
cross join actual_after_dedup

where actual_after_dedup.actual_rows
      <> expected_after_dedup.expected_rows