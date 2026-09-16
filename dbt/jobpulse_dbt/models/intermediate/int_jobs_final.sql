-- models/intermediate/int_jobs_final.sql
-- Surrogate key generation + incremental load logic.
-- Entry point for downstream marts (fact/dimension models).
-- Requires dbt_utils package (see packages.yml).
{{
    config(
        materialized="incremental", unique_key="job_key", incremental_strategy="merge"
    )
}}

with
    source as (select * from {{ ref("int_jobs_cleaned") }}),

    with_key as (

        select
            {{
                dbt_utils.generate_surrogate_key(
                    ["source_job_id", "normalized_job_source", "job_url"]
                )
            }} as job_key, *
        from source

    )

select *
from with_key

{% if is_incremental() %}
    where collected_at > (select max(collected_at) from {{ this }})
{% endif %}
