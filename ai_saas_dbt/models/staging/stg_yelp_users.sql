WITH source AS (
    SELECT * FROM {{ source('raw', 'yelp_users') }}
),

cleaned AS (
    SELECT
        -- Identifiers
        user_id,
        name,

        -- Metrics
        review_count,
        fans,
        average_stars,

        -- Dates
        yelping_since,
        DATE_TRUNC('month', yelping_since)  AS cohort_month,
        DATE_TRUNC('year',  yelping_since)  AS cohort_year,

        -- User segmentation
        CASE
            WHEN review_count >= 100 THEN 'Power User'
            WHEN review_count >= 20  THEN 'Regular User'
            WHEN review_count >= 5   THEN 'Casual User'
            ELSE 'New User'
        END AS user_segment,

        -- Engagement level based on fans
        CASE
            WHEN fans >= 100 THEN 'Influencer'
            WHEN fans >= 10  THEN 'Active'
            ELSE 'Standard'
        END AS influence_tier,

        loaded_at

    FROM source
    WHERE yelping_since IS NOT NULL
)

SELECT * FROM cleaned