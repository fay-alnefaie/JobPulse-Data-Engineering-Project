select *
from (
    select
        *,
        row_number() over (
            partition by job_title, company_name, normalized_city_name
            order by
                case job_source_channel
                    when 'Direct' then 1
                    when 'Aggregated via Sabbar' then 2
                    when 'Aggregated via Tanqeeb' then 3
                    else 4
                end
        ) as priority_rank,
        count(*) over (
            partition by job_title, company_name, normalized_city_name
        ) as channel_duplicate_count
    from {{ ref('int_jobs_final') }}
)
where priority_rank = 1