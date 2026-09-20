with source as (

    select
        job_key,
        skill_name,
        skill_category,
        confidence,
        evidence_span

    from {{ ref('stg_extracted_skills') }}

),

standardized as (

    select
        job_key,
        lower(trim(skill_name)) as skill_name,
        lower(trim(skill_category)) as skill_category,
        confidence,
        evidence_span,
        confidence >= 0.85 as is_high_confidence

    from source

    where confidence >= 0.85

)

select
    job_key,
    skill_name,
    skill_category,
    confidence,
    evidence_span,
    is_high_confidence

from standardized