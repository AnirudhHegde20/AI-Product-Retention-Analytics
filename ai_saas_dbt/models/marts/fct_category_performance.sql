WITH launch_data AS (
    -- Reference marts model, not staging directly
    SELECT * FROM {{ ref('fct_launch_performance') }}
),

category_summary AS (
    SELECT
        category,

        -- How many products in this category?
        COUNT(*)                            AS total_launches,

        -- Average upvotes across category
        ROUND(AVG(upvotes), 0)              AS avg_upvotes,

        -- Best performing product in category
        MAX(upvotes)                        AS max_upvotes,

        -- How many are top performers?
        SUM(CASE WHEN is_top_performer 
            THEN 1 ELSE 0 END)              AS top_performer_count,

        -- Average success score
        ROUND(AVG(success_score), 2)        AS avg_success_score,

        -- Average days since launch
        ROUND(AVG(days_since_launch), 0)    AS avg_days_since_launch

    FROM launch_data
    GROUP BY category
)

SELECT 
    *,
    -- What % of launches in this category are top performers?
    ROUND(
        top_performer_count::NUMERIC / total_launches * 100
    , 0) AS top_performer_pct
FROM category_summary
ORDER BY avg_success_score DESC