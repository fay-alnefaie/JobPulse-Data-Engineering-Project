-- Business/data interpretation:
-- 1. Use the raw job_category when it's present (cleaned/standardized).
-- 2. Fallback: derive category from job_title keywords when raw is empty.
-- No exclusion filtering yet -- categories are kept open, just cleaned/classified.
with
    source as (select * from {{ ref("int_jobs_experience") }}),

    category_from_title as (

        select
            *,
            case
                when job_title ilike '%engineer%' or job_title ilike '%engineering%'
                then 'Engineering'

                when
                    job_title ilike '%developer%'
                    or job_title ilike '%software%'
                    or job_title ilike '%data %'
                    or job_title ilike '% it %'
                    or job_title ilike '% it'
                    or job_title ilike 'it %'
                    or job_title ilike '%information technology%'
                    or job_title ilike '%network%'
                    or job_title ilike '%system admin%'
                then 'IT'

                when
                    job_title ilike '%admin%'
                    or job_title ilike '%office manager%'
                    or job_title ilike '%secretary%'
                    or job_title ilike '%coordinator%'
                then 'Administrative'

                when
                    job_title ilike '%sales%'
                    or job_title ilike '%account manager%'
                    or job_title ilike '%business development%'
                then 'Sales'

                when job_title ilike '%marketing%' or job_title ilike '%social media%'
                then 'Marketing'

                when
                    job_title ilike '%hr %'
                    or job_title ilike '%human resources%'
                    or job_title ilike '%recruit%'
                then 'HR'

                when
                    job_title ilike '%finance%'
                    or job_title ilike '%accountant%'
                    or job_title ilike '%accounting%'
                then 'Finance'

                when job_title ilike '%Analyst%'
                then 'Analyst'

                when job_title ilike '%Receptionist%'
                then 'Receptionist'

                when
                    job_title ilike '%nurse%'
                    or job_title ilike '%doctor%'
                    or job_title ilike '%physician%'
                    or job_title ilike '%pharmacist%'
                    or job_title ilike '%medical%'
                    or job_title ilike '%clinic%'
                    or job_title ilike '%dentist%'
                then 'Healthcare / Medical'

                else null
            end as title_derived_category

        from source

    ),

    category_final as (

        select
            *,

            case
                when trim(coalesce(job_category, '')) != ''
                then initcap(trim(job_category))
                else title_derived_category
            end as normalized_job_category,

            (
                trim(coalesce(job_category, '')) != ''
                or title_derived_category is not null
            ) as has_category_data,

            (
                trim(coalesce(job_category, '')) = ''
                and title_derived_category is not null
            ) as is_category_derived_from_title

        from category_from_title

    )

select *
from category_final
