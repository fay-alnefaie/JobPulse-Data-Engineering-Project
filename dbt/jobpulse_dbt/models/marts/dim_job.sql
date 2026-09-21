-- {{ config(materialized="table") }}

select distinct
    job_key,
    source_job_id,
    job_title, 
    normalized_job_category as job_category,
    normalized_job_status as job_status,
    seniority_level 
    
from {{ ref('snapshot_job_status') }}

where job_key is not null
  and dbt_valid_to is null