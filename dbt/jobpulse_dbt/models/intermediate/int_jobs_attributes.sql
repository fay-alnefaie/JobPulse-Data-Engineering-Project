-- Normalize categorical job attributes and source/channel information.

with source as (

    select *
    from {{ ref('int_jobs_dates') }}

),

normalized as (

    select
        *,

        case
            when upper(trim(workplace_type)) in ('ON-SITE', 'ONSITE', 'ON SITE')
            then 'On-site'
            when upper(trim(workplace_type)) = 'REMOTE'
            then 'Remote'
            when upper(trim(workplace_type)) = 'HYBRID'
            then 'Hybrid'
            when upper(trim(workplace_type)) = 'FIELD'
            then 'Field'
            else workplace_type
        end as normalized_workplace_type,

        case
            when upper(trim(employment_type)) in (
                'FULL TIME',
                'FULL_TIME',
                'FULLTIME'
            )
            then 'Full Time'

            when upper(trim(employment_type)) in (
                'PART TIME',
                'PART_TIME',
                'PARTTIME'
            )
            then 'Part Time'

            when upper(trim(employment_type)) in ('CONTRACT', 'CONTRACTOR')
            then 'Contract'

            when upper(trim(employment_type)) in (
                'FREELANCE/ PROJECT',
                'FREELANCE',
                'PROJECT'
            )
            then 'Freelance / Project'

            when upper(trim(employment_type)) in (
                'TEMPORARY EMPLOYEE',
                'TEMPORARY'
            )
            then 'Temporary'

            when upper(trim(employment_type)) = 'SEASONAL'
            then 'Seasonal'

            when upper(trim(employment_type)) = 'INTERNSHIP'
            then 'Internship'

            else employment_type
        end as normalized_employment_type,

        case
            when upper(trim(job_status)) = 'ACTIVE'
            then 'Active'
            when upper(trim(job_status)) = 'CLOSED'
            then 'Closed'
            when upper(trim(job_status)) = 'EXPIRED'
            then 'Expired'
            else job_status
        end as normalized_job_status,

        case
            when upper(trim(job_source)) = 'AGGREGATED (SOURCE NOT SPECIFIED)'
            then null
            else initcap(trim(job_source))
        end as normalized_job_source,

        case
            when job_url like '%tanqeeb.com%'
             and upper(trim(job_source)) != 'TANQEEB'
            then 'Aggregated via Tanqeeb'

            when job_url like '%sabbar.com%'
             and upper(trim(job_source)) = 'AGGREGATED (SOURCE NOT SPECIFIED)'
            then 'Aggregated via Sabbar'

            else 'Direct'
        end as job_source_channel

    from source

)

select *
from normalized
