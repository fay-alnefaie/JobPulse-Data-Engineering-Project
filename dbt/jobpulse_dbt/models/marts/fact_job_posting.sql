-- {{ config(materialized="table") }}

with jobs as (

    select
        job_key,
        source_job_id,
        company_name,
        company_url_clean,
        normalized_city_name,
        normalized_region_name,
        normalized_country_name,
        normalized_job_source,
        job_source_channel,
        normalized_employment_type,
        normalized_job_posted_date,
        normalized_workplace_type,
        is_salary_disclosed,
        job_url,
        description,
        experience_min_years,
        experience_max_years
        experience_is_open_ended,
        collected_at

    from {{ ref('int_jobs_final') }}

    where job_key is not null

)

select

    row_number() over (
        order by
            job_key,
            source_job_id,
            job_url
    ) as job_posting_key,

    j.job_key,

    {{ dbt_utils.generate_surrogate_key([
        'company_name',
        'company_url'
    ]) }} as company_key,

    {{ dbt_utils.generate_surrogate_key([
        'normalized_city_name',
        'normalized_region_name',
        'normalized_country_name'
    ]) }} as location_key,

    {{ dbt_utils.generate_surrogate_key([
        'normalized_job_source',
        'job_source_channel'
    ]) }} as source_key,

    case
        when normalized_employment_type is null then null
        else {{ dbt_utils.generate_surrogate_key([
            'normalized_employment_type'
        ]) }}
    end as employment_type_key,

    d.date_key as job_posted_date_key,

    j.normalized_workplace_type as workplace_type,
    j.is_salary_disclosed,
    j.job_url,
    j.description,
    j.experience_min_years,
    j.experience_max_years,
    j.experience_is_open_ended,
    j.collected_at

from jobs j

left join {{ ref('dim_date') }} d
    on j.normalized_job_posted_date = d.full_date