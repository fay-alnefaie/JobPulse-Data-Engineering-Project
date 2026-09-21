-- Business decision: project scope limited to these 10 categories only.
-- Documented decision, not a data quality fix.
select *
from {{ ref('int_jobs_category') }}
where normalized_job_category in (
    'Engineering', 'IT', 'Administrative',
    'Sales', 'Marketing', 'HR', 'Finance',
    'Analyst','Receptionist','Healthcare / Medical'
)