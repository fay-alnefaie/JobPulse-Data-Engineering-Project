-- Business/data interpretation:
-- Gulftalent's scraper selected the wrong HTML tag/id, so company_url
-- actually holds the company NAME text (not a real URL) for every row
-- from this source. Until the source is re-scraped correctly, we treat
-- this source's company_url as invalid rather than keep a misleading value.

with
    source as (select * from {{ ref("int_jobs_industry") }}),

    company_handled as (

        select
            *,

            case
                when normalized_job_source = 'Gulftalent' then null else company_url
            end as company_url_clean,

            case
                when normalized_job_source = 'Gulftalent'
                then false
                else company_url is not null
            end as has_valid_company_url

        from source

    )

select *
from company_handled
