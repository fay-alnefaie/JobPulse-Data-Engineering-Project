-- {{ config(materialized='table') }}

with skills as (

    select distinct
        skill_name,
        skill_category

    from {{ ref('int_skills') }}

    where is_high_confidence = true

)

select
    md5(
        coalesce(skill_name, '') || '|' ||
        coalesce(skill_category, '')
    ) as skill_key,
    skill_name,
    skill_category

from skills