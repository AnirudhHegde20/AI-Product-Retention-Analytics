WITH source AS (
    SELECT * FROM {{ source('raw', 'yelp_reviews') }}
),

cleaned AS (
    SELECT
        -- Identifiers
        review_id,
        user_id,
        business_id,

        -- Metrics
        stars,
        useful,
        funny,
        cool,

        -- Engagement score (combines all interaction signals)
        stars + useful + funny + cool       AS engagement_score,

        -- Dates
        review_date,
        DATE_TRUNC('month', review_date)    AS review_month,
        DATE_TRUNC('year',  review_date)    AS review_year,

        -- Quality flag
        CASE
            WHEN stars >= 4 THEN 'Positive'
            WHEN stars = 3  THEN 'Neutral'
            ELSE 'Negative'
        END AS sentiment,

        loaded_at

    FROM source
    WHERE review_date IS NOT NULL
)

SELECT * FROM cleaned