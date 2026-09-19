{{ config(materialized="table") }}

select distinct
    job_key,
    source_job_id,
    job_title as original_job_title,
    job_category,
    normalized_job_category,
    job_status,
    normalized_job_status,
    seniority_level,
    has_category_data,
    is_category_derived_from_title
from {{ ref('int_jobs_final') }}
where job_key is not null