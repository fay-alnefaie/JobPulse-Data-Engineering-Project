-- models/intermediate/int_jobs_company.sql
-- Business/data interpretation:
-- Gulftalent's scraper selected the wrong HTML tag/id, so company_url
-- actually holds the company NAME text (not a real URL) for every row
-- from this source. Until the source is re-scraped correctly, we treat
-- this source's company_url as invalid rather than keep a misleading value.
--
-- NOTE for later: when Gulftalent is re-scraped with the correct tag,
-- job_url will differ from the current (wrong) values, so job_key will
-- differ too -- the incremental merge will INSERT new correct rows
-- instead of overwriting the old wrong ones. The old Gulftalent rows will
-- need an explicit cleanup step at that point (not handled here).
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
