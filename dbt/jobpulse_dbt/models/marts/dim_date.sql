-- {{ config(materialized="table") }}

select distinct
    to_number(to_char(normalized_job_posted_date, 'YYYYMMDD')) as date_key,
    normalized_job_posted_date as full_date,
    year(normalized_job_posted_date) as year,
    month(normalized_job_posted_date) as month,
    monthname(normalized_job_posted_date) as month_name,
    quarter(normalized_job_posted_date) as quarter,
    day(normalized_job_posted_date) as day,
    dayofweek(normalized_job_posted_date) as day_of_week

from {{ ref('int_jobs_preferred_source') }}

where normalized_job_posted_date is not null