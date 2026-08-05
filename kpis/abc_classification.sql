-- ==============================================================================
-- KPI: ABC Classification
-- ==============================================================================
-- Formula Explanation:
-- This KPI classifies SKUs based on their cumulative revenue contribution.
-- 1. Calculate the total revenue per SKU across all stores.
-- 2. Sort SKUs in descending order of revenue.
-- 3. Calculate the running total of revenue and the cumulative percentage.
-- 4. Classification:
--    'A' Class: SKUs making up the first 70% of cumulative revenue.
--    'B' Class: SKUs making up the next 20% (up to 90%).
--    'C' Class: The remaining bottom 10% of revenue.
-- ==============================================================================

-- FROM HERE THE VIEW CREATION STARTS
CREATE OR REPLACE VIEW view_abc_classification AS
-- Step 1: aggregate total revenue per SKU across the whole month, across all stores
WITH sku_revenue AS (
    SELECT
        sku_id,
        sku_name,
        SUM(total_revenue) AS total_revenue
    FROM fact_daily_sales
    GROUP BY sku_id, sku_name
),

-- Step 2: rank SKUs by revenue, compute cumulative % of total revenue
ranked AS (
    SELECT
        sku_id,
        sku_name,
        total_revenue,
        SUM(total_revenue) OVER (ORDER BY total_revenue DESC) AS running_revenue,
        SUM(total_revenue) OVER () AS grand_total_revenue,
        ROUND(
            SUM(total_revenue) OVER (ORDER BY total_revenue DESC) * 100.0
            / NULLIF(SUM(total_revenue) OVER (), 0)
        , 2) AS cumulative_pct,
        ROUND(
            total_revenue * 100.0
            / NULLIF(SUM(total_revenue) OVER (), 0)
        , 2) AS sku_revenue_pct,
        ROUND(
            COUNT(sku_id) OVER (ORDER BY total_revenue DESC) * 100.0
            / NULLIF(COUNT(sku_id) OVER (), 0)
        , 4) AS cumulative_sku_pct,
        ROUND(
            100.0 / NULLIF(COUNT(sku_id) OVER (), 0)
        , 4) AS sku_pct
    FROM sku_revenue
)

-- Step 3: classify into A/B/C based on cumulative revenue contribution
SELECT
    sku_id,
    sku_name,
    total_revenue,
    sku_revenue_pct,
    cumulative_pct AS cumulative_revenue_pct,
    sku_pct,
    cumulative_sku_pct,
    CASE
        WHEN cumulative_pct <= 70 THEN 'A'
        WHEN cumulative_pct <= 90 THEN 'B'
        ELSE 'C'
    END AS abc_class
FROM ranked
ORDER BY total_revenue DESC;
