{{ config(materialized="table") }}

select distinct
    {{ dbt_utils.generate_surrogate_key(['company_name', 'company_url_clean']) }} as company_key,
    company_name,
    company_url,
    company_url_clean,
    company_industry as industry,
    company_industry_clean as industry_clean,
    has_valid_company_url

from {{ ref('int_jobs_final') }}