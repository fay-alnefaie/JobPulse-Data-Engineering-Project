{{ config(materialized="table") }}

with companies as (

    select
        {{ dbt_utils.generate_surrogate_key([
            'company_name',
            'company_url_clean'
        ]) }} as company_key,

        company_name,
        company_url,
        company_url_clean,
        company_industry as industry,
        company_industry_clean as industry_clean,
        has_valid_company_url,

        row_number() over (
            partition by
                company_name,
                company_url_clean
            order by
                company_name
        ) as rn

    from {{ ref('int_jobs_final') }}

)

select
    company_key,
    company_name,
    company_url,
    company_url_clean,
    industry,
    industry_clean,
    has_valid_company_url

from companies
where rn = 1