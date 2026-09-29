-- Checks that no (job_title, company_name, normalized_city_name) group
-- has more than one row left after deduplication in
-- int_jobs_preferred_source.
select
    job_title,
    company_name,
    normalized_city_name,
    count(*) as duplicate_count
from {{ ref('int_jobs_preferred_source') }}
group by
    job_title,
    company_name,
    normalized_city_name
having count(*) > 1