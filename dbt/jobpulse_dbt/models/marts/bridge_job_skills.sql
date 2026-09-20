{{ config(materialized='table') }}

with job_skills as (

    select
        job_key,
        skill_name,
        skill_category,
        confidence,
        evidence_span

    from {{ ref('int_skills') }}

    where is_high_confidence = true

),

skills_dimension as (

    select
        skill_key,
        skill_name,
        skill_category

    from {{ ref('dim_skills') }}

)

select
    job_skills.job_key,
    skills_dimension.skill_key,
    job_skills.confidence,
    job_skills.evidence_span

from job_skills

inner join skills_dimension
    on job_skills.skill_name = skills_dimension.skill_name
    and job_skills.skill_category = skills_dimension.skill_category