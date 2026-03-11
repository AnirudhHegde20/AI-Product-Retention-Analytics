WITH users AS (
    SELECT
        user_id,
        cohort_month,
        user_segment
    FROM {{ ref('stg_yelp_users') }}
),

review_activity AS (
    SELECT
        user_id,
        MIN(review_date)    AS first_review_date,
        MAX(review_date)    AS last_review_date,
        COUNT(*)            AS total_reviews,
        AVG(stars)          AS avg_stars,
        AVG(engagement_score) AS avg_engagement_score
    FROM {{ ref('stg_yelp_reviews') }}
    GROUP BY user_id
),

survival_data AS (
    SELECT
        u.user_id,
        u.cohort_month,
        u.user_segment,

        -- When did they start and stop?
        r.first_review_date,
        r.last_review_date,

        -- How long did they survive? (in days)
        r.last_review_date - r.first_review_date   AS survival_days,

        -- Engagement signals
        r.total_reviews,
        r.avg_stars,
        r.avg_engagement_score,

        -- Churned = no activity in last 12 months
        CASE
            WHEN r.last_review_date < CURRENT_DATE - INTERVAL '12 months'
            THEN TRUE
            ELSE FALSE
        END AS churned

    FROM users u
    JOIN review_activity r ON u.user_id = r.user_id
)

SELECT * FROM survival_data