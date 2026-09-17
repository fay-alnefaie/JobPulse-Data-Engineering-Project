-- Business/data interpretation:
-- 1. Resolve Sabbar city from the URL when available.
-- 2. Deduplicate using (source_job_id, job_url).

with source as (

    select *
    from {{ ref('stg_jobs') }}

),

city_resolved as (

    select
        *,
        case
            when job_url like '%sabbar.com%'
            then replace(
                regexp_substr(
                    job_url,
                    '/c-(.+?)-r-',
                    1,
                    1,
                    'e',
                    1
                ),
                '-',
                ' '
            )
            else null
        end as url_city_raw,

        coalesce(
            case
                when job_url like '%sabbar.com%'
                then replace(
                    regexp_substr(
                        job_url,
                        '/c-(.+?)-r-',
                        1,
                        1,
                        'e',
                        1
                    ),
                    '-',
                    ' '
                )
            end,
            city
        ) as city_final

    from source

),

deduped as (

    select *
    from city_resolved
    qualify row_number() over (
        partition by source_job_id, job_url
        order by collected_at desc
    ) = 1

)

select *
from deduped
