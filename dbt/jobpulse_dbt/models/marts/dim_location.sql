{{ config(materialized="table") }}

select distinct
    {{ dbt_utils.generate_surrogate_key([
        'normalized_city_name',
        'normalized_region_name',
        'normalized_country_name'
    ]) }} as location_key,

    city,
    normalized_city_name,
    region,
    normalized_region_name,
    country,
    normalized_country_name

from {{ ref('int_jobs_final') }}