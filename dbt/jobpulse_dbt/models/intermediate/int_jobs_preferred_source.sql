{{ config(materialized="table") }}

-- Groups by lowercased/trimmed title+company so casing/whitespace
-- differences don't create fake duplicates. Winner per group:
-- Direct > Sabbar > Tanqeeb, then has a company URL, then newest, then job_key.

select *
from (
    select
        *,
        row_number() over (
            partition by
                trim(lower(job_title)),
                trim(lower(company_name)),
                normalized_city_name
            order by
                case job_source_channel
                    when 'Direct' then 1
                    when 'Aggregated via Sabbar' then 2
                    when 'Aggregated via Tanqeeb' then 3
                    else 4
                end,
                case when company_url_clean is null then 1 else 0 end,
                collected_at desc,
                job_key
        ) as priority_rank,

        count(*) over (
            partition by
                trim(lower(job_title)),
                trim(lower(company_name)),
                normalized_city_name
        ) as channel_duplicate_count

    from {{ ref('int_jobs_final') }}
)
where priority_rank = 1