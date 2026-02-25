WITH staged AS (
    -- Pull from staging, never from raw
    SELECT * FROM {{ ref('stg_product_hunt_launches') }}
),

launch_performance AS (
    SELECT
        -- Identifiers
        id,
        name,
        product_url,
        category,
        launch_date,
        traction_tier,
        upvotes,

        -- Days since launch (how old is this product?)
        CURRENT_DATE - launch_date AS days_since_launch,

        -- Launch success score (0-100)
        ROUND(
            LEAST(upvotes::NUMERIC / 10, 100)
        , 2) AS success_score,

        -- Is this a top performer?
        CASE
            WHEN upvotes >= 700 THEN TRUE
            ELSE FALSE
        END AS is_top_performer,

        -- Which month was it launched?
        TO_CHAR(launch_date, 'YYYY-MM') AS launch_month

    FROM staged
)

SELECT * FROM launch_performance