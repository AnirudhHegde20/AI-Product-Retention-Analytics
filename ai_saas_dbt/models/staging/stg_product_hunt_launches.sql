WITH source AS (
    -- Pull raw data exactly as loaded
    SELECT * FROM {{ source('raw', 'product_hunt_launches') }}
),

cleaned AS (
    SELECT
        -- Identifiers
        id,
        product_url,

        -- Clean text fields
        TRIM(LOWER(name))    AS name,
        TRIM(tagline)        AS tagline,

        -- Metrics
        upvotes,

        -- Standardize category
        CASE
            WHEN category IS NULL THEN 'Uncategorized'
            ELSE TRIM(category)
        END AS category,

        -- Smarter pricing proxy based on upvotes
        CASE
            WHEN upvotes >= 700 THEN 'High Traction'
            WHEN upvotes >= 500 THEN 'Medium Traction'
            ELSE 'Low Traction'
        END AS traction_tier,

        -- Dates
        launch_date,
        scraped_at

    FROM source
)

SELECT * FROM cleaned