-- Checks every foreign key in fact_job_posting (job_key, company_key,
-- location_key, source_key, employment_type_key, job_posted_date_key)
-- points to a row that actually exists in its dimension table.
select
    f.job_posting_key,
    'job_key' as foreign_key_name
from {{ ref('fact_job_posting') }} f
left join {{ ref('dim_job') }} d
    on f.job_key = d.job_key
where f.job_key is not null
  and d.job_key is null

union all

select
    f.job_posting_key,
    'company_key' as foreign_key_name
from {{ ref('fact_job_posting') }} f
left join {{ ref('dim_company') }} d
    on f.company_key = d.company_key
where f.company_key is not null
  and d.company_key is null

union all

select
    f.job_posting_key,
    'location_key' as foreign_key_name
from {{ ref('fact_job_posting') }} f
left join {{ ref('dim_location') }} d
    on f.location_key = d.location_key
where f.location_key is not null
  and d.location_key is null

union all

select
    f.job_posting_key,
    'source_key' as foreign_key_name
from {{ ref('fact_job_posting') }} f
left join {{ ref('dim_source') }} d
    on f.source_key = d.source_key
where f.source_key is not null
  and d.source_key is null

union all

select
    f.job_posting_key,
    'employment_type_key' as foreign_key_name
from {{ ref('fact_job_posting') }} f
left join {{ ref('dim_employment_type') }} d
    on f.employment_type_key = d.employment_type_key
where f.employment_type_key is not null
  and d.employment_type_key is null

union all

select
    f.job_posting_key,
    'job_posted_date_key' as foreign_key_name
from {{ ref('fact_job_posting') }} f
left join {{ ref('dim_date') }} d
    on f.job_posted_date_key = d.date_key
where f.job_posted_date_key is not null
  and d.date_key is null