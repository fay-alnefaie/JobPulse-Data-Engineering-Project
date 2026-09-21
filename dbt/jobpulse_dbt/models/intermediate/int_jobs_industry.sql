-- Business/data interpretation:
-- ~58% of rows have industry = NULL. Source breakdown confirmed this is a
-- structural gap (some scraping sources never expose industry), not random
-- missingness -- so we represent it explicitly rather than guessing a value.
-- industry is categorical/text, so a text placeholder is safe here (unlike
-- numeric columns such as experience_years, which are never backfilled).
with
    source as (select * from {{ ref("int_jobs_category_filtered") }}),

    industry_handled as (

        select
            *,

            coalesce(
                nullif(trim(company_industry), ''), 'Not Specified'
            ) as company_industry_clean,

            (
                company_industry is not null and trim(company_industry) != ''
            ) as has_company_industry_data

        from source

    )

select *
from industry_handled
