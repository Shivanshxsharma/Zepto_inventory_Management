-- ==============================================================================
-- KPI: Sales Velocity
-- ==============================================================================
-- Formula Explanation:
-- 1. Standard Sales Velocity: 
--    Total Units Sold / Total Calendar Days in Period
--    (Indicates the raw average units sold per day across the whole month)
-- 2. Adjusted Sales Velocity: 
--    Total Units Sold / Days Available for Sale
--    (Adjusts for stockouts by only counting days where the item was in stock)
-- 3. Classification:
--    Fast-moving: Top 30% of SKUs by velocity
--    Medium-moving: Next 40% of SKUs
--    Slow-moving: Bottom 30% of SKUs
-- ==============================================================================

-- FROM HERE THE VIEW CREATION STARTS
CREATE OR REPLACE VIEW view_sales_velocity AS
WITH sku_aggregates AS (
    SELECT 
        v.store_id,
        v.sku_id,
        SUM(v.total_quantity_sold) AS total_units_sold,
        90 AS period_days,
        SUM(CASE WHEN (v.opening_stock + v.total_quantity_purchased) > 0 THEN 1 ELSE 0 END) AS days_available
    FROM view_inventory_snapshot v
    WHERE v.movement_date BETWEEN '2025-01-01' AND '2025-03-31'
    GROUP BY 
        v.store_id, 
        v.sku_id
),
velocity_calculations AS (
    SELECT 
        a.store_id,
        a.sku_id,
        a.total_units_sold,
        a.period_days,
        a.days_available,
        (a.total_units_sold / a.period_days) AS sales_velocity,
        (a.total_units_sold / NULLIF(a.days_available, 0)) AS adjusted_velocity_days_available
    FROM sku_aggregates a
),
ranked_velocity AS (
    SELECT 
        v.store_id,
        v.sku_id,
        v.total_units_sold,
        v.sales_velocity,
        v.adjusted_velocity_days_available,
        NTILE(10) OVER (PARTITION BY v.store_id ORDER BY v.sales_velocity DESC) AS velocity_decile
    FROM velocity_calculations v
)
SELECT 
    r.store_id,
    ds.store_name,
    r.sku_id,
    p.sku_name,
    p.category,
    r.total_units_sold,
    r.sales_velocity,
    r.adjusted_velocity_days_available,
    CASE 
        WHEN r.velocity_decile IN (1, 2, 3) THEN 'Fast-moving'
        WHEN r.velocity_decile IN (4, 5, 6, 7) THEN 'Medium-moving'
        ELSE 'Slow-moving'
    END AS classification
FROM ranked_velocity r
JOIN dark_stores ds ON r.store_id = ds.store_id
JOIN products p ON r.sku_id = p.sku_id
ORDER BY 
    r.sales_velocity DESC;
