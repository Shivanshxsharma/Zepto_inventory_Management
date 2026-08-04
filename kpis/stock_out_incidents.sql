-- ==============================================================================
-- KPI: Stock Out Incidents
-- ==============================================================================
-- Formula Explanation:
-- Cumulative Purchased = Running total of purchases since the beginning of time
-- Cumulative Sold = Running total of sales since the beginning of time
-- Closing Stock = Cumulative Purchased - Cumulative Sold
-- 
-- A Stock Out Incident occurs when a store completely runs out of a specific SKU 
-- on a given day, identified mathematically when the calculated Closing Stock <= 0.
-- ==============================================================================

-- FROM HERE THE VIEW CREATION STARTS
CREATE OR REPLACE VIEW view_stock_out_incidents AS
WITH running_inventory AS (
    SELECT 
        store_id,
        store_name,
        sku_id,
        sku_name,
        movement_date,
        SUM(total_quantity_purchased) OVER (
            PARTITION BY store_id, sku_id 
            ORDER BY movement_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_purchased,
        
        SUM(total_quantity_sold) OVER (
            PARTITION BY store_id, sku_id 
            ORDER BY movement_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_sold,
        
        SUM(total_quantity_purchased - total_quantity_sold) 
            OVER (
                PARTITION BY store_id, sku_id 
                ORDER BY movement_date
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS closing_stock
    FROM fact_daily_movement
)
SELECT 
    store_id,
    store_name,
    sku_id,
    sku_name,
    movement_date AS stock_out_date,
    cumulative_purchased,
    cumulative_sold,
    closing_stock
FROM running_inventory
WHERE closing_stock <= 0;
