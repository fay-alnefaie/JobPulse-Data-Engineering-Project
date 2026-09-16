-- models/marts/int_jobs_cleaned.sql
-- Final cleaned dataset used by downstream dimensions/facts.
-- Keep this model if the existing marts currently expect one wide cleaned table.
select
    source_job_id,

    job_title,
    job_category,
    normalized_job_category,
    has_category_data,
    is_category_derived_from_title,
    company_industry,
    company_industry_clean,
    has_company_industry_data,

    company_name,
    company_url,
    company_url_clean,
    has_valid_company_url,

    city,
    normalized_city_name,
    region,
    normalized_region_name,
    country,
    normalized_country_name,

    employment_type,
    normalized_employment_type,
    workplace_type,
    normalized_workplace_type,

    experience_years,
    experience_min_years,
    experience_max_years,
    experience_is_open_ended,
    seniority_level,

    job_status,
    normalized_job_status,

    is_salary_disclosed,

    job_url,
    normalized_job_source,
    job_source_channel,

    job_posted_date,
    normalized_job_posted_date,
    collected_at,

    description

from {{ ref("int_jobs_company") }}
