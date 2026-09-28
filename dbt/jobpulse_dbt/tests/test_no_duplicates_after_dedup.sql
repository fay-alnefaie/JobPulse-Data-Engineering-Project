-- Verify that no duplicate jobs remain after deduplication.
-- Duplicate key: (source_job_id, job_url)
-- Test passes when 0 rows are returned.

select
    source_job_id,
    job_url,
    count(*) as duplicate_count

from {{ ref('int_jobs_city_deduped') }}

group by
    source_job_id,
    job_url

having count(*) > 1