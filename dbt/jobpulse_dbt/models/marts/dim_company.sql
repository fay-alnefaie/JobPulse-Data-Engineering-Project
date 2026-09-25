{{ config(materialized="table") }}

with companies as (

    select
        {{ dbt_utils.generate_surrogate_key([
            'company_name',
            'company_url_clean'
        ]) }} as company_key,

        company_name,
        company_url_clean as company_url,
        company_industry_clean as company_industry,

        row_number() over (
            partition by
                company_name,
                company_url_clean
            order by
                case
                    when company_industry_clean is not null then 1
                    else 2
                end,
                company_industry_clean
        ) as rn

    from {{ ref('int_jobs_preferred_source') }}

)

select
    company_key,
    company_name,
    company_url,
    company_industry

from companies
where rn = 1
