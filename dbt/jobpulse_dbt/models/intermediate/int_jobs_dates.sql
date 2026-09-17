-- Interpret relative and explicit job-posted dates.

with source as (

    select *
    from {{ ref('int_jobs_country') }}

),

normalized_dates as (

    select
        *,
        case

            when lower(trim(job_posted_date)) = 'yesterday'
            then dateadd(day, -1, date(collected_at))

            when lower(trim(job_posted_date)) like '%minute%'
            then date(
                dateadd(
                    minute,
                    -1 * try_cast(
                        regexp_substr(job_posted_date, '\\d+') as int
                    ),
                    collected_at
                )
            )

            when lower(trim(job_posted_date)) like '%hour%'
            then date(
                dateadd(
                    hour,
                    -1 * try_cast(
                        regexp_substr(job_posted_date, '\\d+') as int
                    ),
                    collected_at
                )
            )

            when lower(trim(job_posted_date)) like '%week%'
            then date(
                dateadd(
                    day,
                    -7 * try_cast(
                        regexp_substr(job_posted_date, '\\d+') as int
                    ),
                    collected_at
                )
            )

            when lower(trim(job_posted_date)) in (
                'sunday',
                'monday',
                'tuesday',
                'wednesday',
                'thursday',
                'friday',
                'saturday'
            )
            then dateadd(
                day,
                -1 * mod(
                    dayofweek(collected_at) - case lower(trim(job_posted_date))
                        when 'sunday' then 0
                        when 'monday' then 1
                        when 'tuesday' then 2
                        when 'wednesday' then 3
                        when 'thursday' then 4
                        when 'friday' then 5
                        when 'saturday' then 6
                    end + 7,
                    7
                ),
                date(collected_at)
            )

            when lower(trim(job_posted_date)) like '%day%'
            then date(
                dateadd(
                    day,
                    -1 * try_cast(
                        regexp_substr(job_posted_date, '\\d+') as int
                    ),
                    collected_at
                )
            )

            when try_to_date(job_posted_date, 'DD MON YYYY') is not null
            then try_to_date(job_posted_date, 'DD MON YYYY')

            when try_to_date(job_posted_date) is not null
            then try_to_date(job_posted_date)

            else null

        end as normalized_job_posted_date

    from source

)

select *
from normalized_dates
