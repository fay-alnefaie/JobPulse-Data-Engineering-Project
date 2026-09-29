-- Checks experience numbers make sense: no negative years, min not
-- greater than max, and nothing unrealistically high (over 50 years).
SELECT *
FROM {{ ref('int_jobs_final') }}
WHERE
    experience_min_years < 0
    OR experience_max_years < 0
    OR experience_min_years > experience_max_years
    OR experience_max_years > 50