{% snapshot snapshot_job_status %}

{{
    config(
        target_schema='silver',
        unique_key='job_key',
        strategy='check',
        check_cols=['normalized_job_status']
    )
}}

select * from {{ ref('int_jobs_final') }}

{% endsnapshot %}