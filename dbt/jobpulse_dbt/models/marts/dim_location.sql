{{ config(materialized="table") }}

with locations as (

    select
        {{ dbt_utils.generate_surrogate_key([
            'normalized_city_name',
            'normalized_region_name',
            'normalized_country_name'
        ]) }} as location_key,

    
        normalized_city_name as city,
        normalized_region_name as region,
        normalized_country_name as country,

        row_number() over (
            partition by
                normalized_city_name,
                normalized_region_name,
                normalized_country_name
            order by
                city
        ) as rn

    from {{ ref('int_jobs_final') }}

)

select
    location_key,
    city,
    normalized_city_name,
    region,
    normalized_region_name,
    country,
    normalized_country_name

from locations
where rn = 1