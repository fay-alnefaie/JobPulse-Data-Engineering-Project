with source as (

    select
        job_key,
        trim(skill_name) as skill_name,
        lower(trim(skill_category)) as skill_category,
        confidence,
        trim(evidence_span) as evidence_span

    from {{ source('jobpulse', 'extracted_skills') }}

    where job_key is not null
      and skill_name is not null

),

deduplicated as (

    select
        *,
        row_number() over (
            partition by job_key, lower(skill_name)
            order by confidence desc
        ) as row_number

    from source

)

select
    job_key,
    skill_name,
    skill_category,
    confidence,
    evidence_span

from deduplicated

where row_number = 1