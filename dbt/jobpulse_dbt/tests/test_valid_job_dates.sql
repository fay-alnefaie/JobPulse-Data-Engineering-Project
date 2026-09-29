with parsed_dates as (

    select
        *,

        coalesce(
            try_to_date(job_posted_date::varchar),
            try_to_date(job_posted_date::varchar, 'DD MON YYYY')
        ) as parsed_job_posted_date,

        coalesce(
            try_to_date(collected_at::varchar),
            try_to_date(collected_at::varchar, 'DD MON YYYY')
        ) as parsed_collected_date

    from {{ ref('int_jobs_final') }}

)

select *
from parsed_dates

where
    (
        parsed_job_posted_date is not null
        and parsed_collected_date is not null
        and parsed_job_posted_date > parsed_collected_date
    )

    or

    (
        parsed_job_posted_date is not null
        and parsed_job_posted_date > current_date()
    )