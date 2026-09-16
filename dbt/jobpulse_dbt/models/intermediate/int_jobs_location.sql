-- models/intermediate/int_jobs_location.sql
-- Normalize city, region, and country using the mapping seed plus fallback rules.

with source as (

    select *
    from {{ ref('int_jobs_city_deduped') }}

),

with_city_region as (

    select
        d.*,
        upper(trim(d.city_final, ' ''')) as city_lookup_key,
        m.mapped_city as normalized_city_name,
        m.mapped_region as seed_mapped_region

    from source d
    left join {{ ref('city_region_mapping') }} m
        on upper(trim(d.city_final, ' ''')) = m.raw_value_normalized

),

normalized_region as (

    select
        *,
        case
            when region like '%&amp;#%'
              or region like '%&Amp;#%'
            then null

            when seed_mapped_region is not null
             and trim(seed_mapped_region) != ''
            then seed_mapped_region

            when initcap(region) in (
                'Riyadh',
                'Riyadh Region',
                'Riyadh Province'
            )
            then 'Riyadh Province'

            when initcap(region) in (
                'Jeddah',
                'Taif',
                'At Taif',
                'Mecca',
                'Jiddah',
                'Makkah',
                'Makkah Region',
                'Saudi Arabia-Jeddah',
                'Saudi Arabia - Jeddah',
                'Saudi Arabia - Taif'
            )
            then 'Makkah Al-Mukarramah Province'

            when initcap(region) in (
                'Eastern',
                'Eastern Province',
                'Dammam',
                'Dhahran',
                'Khobar',
                'Dhahran/ Al-Khobar (Hub-Based With Regional Coverage)',
                'Al-Khobar'
            )
            then 'Eastern Province'

            when initcap(region) in ('Madinah', 'Madinah Region')
            then 'Al-Madinah Al-Munawwarah Province'

            when initcap(region) in ('Qassim', 'Qassim Region')
            then 'Qassim Province'

            when initcap(region) in (
                'Northern Borders',
                'Northern Borders Region'
            )
            then 'Northern Borders Province'

            when initcap(region) in ('Hail', 'Hail Region')
            then 'Hail Province'

            when initcap(region) in (
                'Tabuk',
                'Tabuk Region',
                'Neom',
                'Amaala'
            )
            then 'Tabuk Province'

            when initcap(region) in (
                'Al Jouf',
                'Al Jouf Region',
                'Jouf'
            )
            then 'Al-Jawf Province'

            when initcap(region) in (
                'Al Baha',
                'Al Bahah Region',
                'Bahah'
            )
            then 'Al-Bahah Province'

            when initcap(region) in (
                'Asir',
                'Asir Region',
                'Aseer',
                '''Asir'
            )
            then 'Aseer Province'

            when initcap(region) in ('Najran', 'Najran Region')
            then 'Najran Province'

            when initcap(region) in (
                'Jazan',
                'Jazan Region',
                'Gezan'
            )
            then 'Jazan Province'

            when initcap(region) in (
                'Western',
                'Western Region',
                'Western Province'
            )
            then 'Makkah Al-Mukarramah Province'

            when initcap(region) in (
                'Central',
                'Central Region',
                'Central Province'
            )
            then 'Riyadh Province'

            when initcap(region) like 'Saudi Arabia - %'
            then replace(initcap(region), 'Saudi Arabia - ', '')

            when initcap(region) = 'Saudi Arabia'
            then null

            else initcap(region)
        end as normalized_region_name

    from with_city_region

),

normalized_country as (

    select
        *,
        case
            when country = 'Saudi'
            then 'Saudi Arabia'
            else country
        end as normalized_country_name

    from normalized_region

)

select *
from normalized_country
