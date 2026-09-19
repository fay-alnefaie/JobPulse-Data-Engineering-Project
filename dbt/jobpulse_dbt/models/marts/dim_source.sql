{{ config(materialized="table") }}

select distinct
    {{ dbt_utils.generate_surrogate_key([
        'normalized_job_source',
        'job_source_channel'
    ]) }} as source_key,

    normalized_job_source as source_name,
    job_source_channel as source_channel

from {{ ref('int_jobs_final') }}

where normalized_job_source is not null