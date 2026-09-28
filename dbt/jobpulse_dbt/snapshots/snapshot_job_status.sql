{% snapshot snapshot_job_status %}

{{
    config(
        target_schema='silver',
        unique_key='job_key',
        strategy='check',
        check_cols=['normalized_job_status', 'normalized_job_category', 'seniority_level'],
        hard_deletes='invalidate'
    )
}}

select * from {{ ref('int_jobs_final') }}

{% endsnapshot %}