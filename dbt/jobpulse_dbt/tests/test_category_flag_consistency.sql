with category_data as (

    select
        *,
        try_to_boolean(has_category_data::varchar) as category_flag,
        nullif(trim(normalized_job_category::varchar), '') as category_value

    from {{ ref('int_jobs_final') }}

)

select *
from category_data

where
    (
        category_flag = true
        and category_value is null
    )

    or

    (
        category_flag = false
        and category_value is not null
    )