-- models/intermediate/int_jobs_experience.sql
-- Interpret experience text as min/max years.
-- Date-like values such as 02/05/2026 are rejected as experience data.
with
    source as (select * from {{ ref("int_jobs_attributes") }}),

    experience_numbers as (

        select
            *,
            trim(experience_years) as experience_years_clean,

            regexp_like(
                trim(experience_years), '^\\d{1,2}/\\d{1,2}/\\d{4}$'
            ) as is_date_like,

            try_cast(regexp_substr(experience_years, '\\d+', 1, 1) as int) as exp_num1,

            try_cast(regexp_substr(experience_years, '\\d+', 1, 2) as int) as exp_num2,

            (
                experience_years ilike '%fresh%'
                or experience_years ilike '%no experience%'
            ) as is_fresh,

            (experience_years like '%+%') as is_open_ended,

            (
                experience_years ilike '%up to%' or experience_years ilike '%less than%'
            ) as is_upper_bound_only

        from source

    ),

    experience_parsed as (

        select
            *,

            case
                when experience_years_clean is null or is_date_like
                then null

                when is_fresh
                then 0

                when is_upper_bound_only
                then 0

                else exp_num1
            end as experience_min_years,

            case
                when experience_years_clean is null or is_date_like
                then null

                when is_fresh
                then 0

                when is_upper_bound_only
                then coalesce(exp_num1, exp_num2)

                when is_open_ended
                then null

                when exp_num2 is not null
                then exp_num2

                else exp_num1
            end as experience_max_years,

            case
                when is_date_like then false else is_open_ended
            end as experience_is_open_ended

        from experience_numbers

    ),

    seniority_levels as (
        select
            *,
            case
                when experience_min_years is null
                then 'Not Specified'

                when is_open_ended and experience_min_years >= 10
                then 'Executive / Director'
                when is_open_ended and experience_min_years >= 5
                then 'Senior-level'
                when is_open_ended and experience_min_years >= 3
                then 'Associate / Mid-level'
                when is_open_ended
                then 'Entry-level'

                when experience_max_years <= 2
                then 'Entry-level'
                when experience_max_years <= 5
                then 'Associate / Mid-level'
                when experience_max_years <= 10
                then 'Senior-level'
                else 'Executive / Director'
            end as seniority_level
        from experience_parsed

    )

select *
from seniority_levels
