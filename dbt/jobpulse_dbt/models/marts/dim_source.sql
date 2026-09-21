-- {{ config(materialized="table") }}

select distinct
    {{ dbt_utils.generate_surrogate_key([
        'normalized_job_source',
        'job_source_channel'
    ]) }} as source_key,

    coalesce(
        normalized_job_source,
        'Not Specified'
    ) as source_name,

    job_source_channel as source_channel

from {{ ref('int_jobs_final') }}