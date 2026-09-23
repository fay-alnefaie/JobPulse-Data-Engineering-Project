-- {{ config(materialized="table") }}

select distinct
    {{ dbt_utils.generate_surrogate_key([
        'normalized_employment_type'
    ]) }} as employment_type_key,

    normalized_employment_type as employment_type_name

from {{ ref('int_jobs_preferred_source') }}

where normalized_employment_type is not null