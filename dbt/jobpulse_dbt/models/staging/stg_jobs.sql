-- Technical cleaning only: rename, trim, type casting, and basic string cleanup.
with
    source as (select * from raw.jobs_raw),

    cleaned as (

        select
            source_job_id,
            replace(job_title, ' 📣 Job Ad', '') as job_title,
            url as job_url,
            company_name,
            company_url,
            replace(industry, ' &amp; ', ' & ') as company_industry,
            city,
            region,
            country,
            employment_type,
            workplace_type,
            experience_years,
            job_category,
            try_to_boolean(is_salary_disclosed) as is_salary_disclosed,
            try_to_timestamp_ntz(collected_at) as collected_at,
            replace(job_source, '.com', '') as job_source,
            job_posted_date,
            job_status,
            description

        from source
        where source_job_id is not null and trim(source_job_id) != ''

    )

select *
from cleaned
