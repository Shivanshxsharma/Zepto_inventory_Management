-- ==============================================================================
-- KPI: Inventory Turnover Ratio and Days of Inventory on Hand (DOH)
-- ==============================================================================
-- Formula Explanation:
-- Average Inventory = (Opening Stock + Closing Stock) / 2.0
-- Inventory Turnover Ratio = Total Units Sold / Average Inventory
--   * A higher ratio means inventory is sold and replaced more frequently.
-- Days of Inventory on Hand (DOH) = 90.0 / Inventory Turnover Ratio
--   * Indicates how many days the current average inventory will last at 
--     the current sales rate (assuming a 90-day quarter).
-- ==============================================================================

-- FROM HERE THE VIEW CREATION STARTS
CREATE OR REPLACE VIEW view_inventory_turnover AS
SELECT
    store_id,
    store_name,
    sku_id,
    sku_name,
    SUM(total_quantity_sold) AS total_units_sold,
    AVG((opening_stock + closing_stock) / 2.0) AS avg_inventory,
    ROUND(
        SUM(total_quantity_sold) * 1.0 /
        NULLIF(AVG((opening_stock + closing_stock) / 2.0), 0)
    , 2) AS inventory_turnover_ratio,
    ROUND(
        90.0 /
        NULLIF(
            SUM(total_quantity_sold) * 1.0 /
            NULLIF(AVG((opening_stock + closing_stock) / 2.0), 0)
        , 0)
    , 1) AS days_of_inventory_on_hand
FROM view_inventory_snapshot
WHERE movement_date BETWEEN '2025-01-01' AND '2025-03-31'
GROUP BY store_id, store_name, sku_id, sku_name
ORDER BY inventory_turnover_ratio DESC;
