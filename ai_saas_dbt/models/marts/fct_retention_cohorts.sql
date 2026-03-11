WITH users AS (
    SELECT
        user_id,
        cohort_month
    FROM {{ ref('stg_yelp_users') }}
),

reviews AS (
    SELECT
        user_id,
        review_month
    FROM {{ ref('stg_yelp_reviews') }}
),

-- For each user, find their cohort (first month) and activity month
user_activity AS (
    SELECT
        u.user_id,
        u.cohort_month,
        r.review_month                                      AS activity_month,

        -- How many months after joining did they write this review?
        EXTRACT(YEAR FROM AGE(r.review_month, u.cohort_month)) * 12 +
        EXTRACT(MONTH FROM AGE(r.review_month, u.cohort_month)) AS months_since_joining

    FROM users u
    JOIN reviews r ON u.user_id = r.user_id
),

-- Count cohort sizes and retained users per month
cohort_retention AS (
    SELECT
        cohort_month,
        months_since_joining,

        -- How many unique users active in this month?
        COUNT(DISTINCT user_id)                             AS active_users

    FROM user_activity
    WHERE months_since_joining >= 0
    GROUP BY cohort_month, months_since_joining
),

-- Get cohort sizes (month 0 = all users who joined)
cohort_sizes AS (
    SELECT
        cohort_month,
        active_users                                        AS cohort_size
    FROM cohort_retention
    WHERE months_since_joining = 0
)

SELECT
    cr.cohort_month,
    cr.months_since_joining,
    cr.active_users,
    cs.cohort_size,

    -- Retention rate as percentage
    ROUND(
        cr.active_users::NUMERIC / cs.cohort_size * 100
    , 2)                                                    AS retention_rate

FROM cohort_retention cr
JOIN cohort_sizes cs ON cr.cohort_month = cs.cohort_month
ORDER BY cr.cohort_month, cr.months_since_joining