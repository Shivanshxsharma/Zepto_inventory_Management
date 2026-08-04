-- snapshot.sql
-- Creates a daily inventory snapshot showing opening and closing stock for every movement day.

USE zepto_inventory;

CREATE OR REPLACE VIEW view_inventory_snapshot AS
WITH daily_running_stock AS (
    SELECT 
        store_id,
        store_name,
        sku_id,
        sku_name,
        movement_date,
        total_quantity_purchased,
        total_quantity_sold,
        -- Closing stock is the cumulative sum of all purchases minus all sales till today
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
    movement_date,
    
    -- Today's Opening Stock is simply today's Closing Stock 
    -- reversing out today's movement (+ sold - purchased)
    (closing_stock + total_quantity_sold - total_quantity_purchased) AS opening_stock,
    
    total_quantity_purchased,
    total_quantity_sold,
    closing_stock
FROM daily_running_stock
WHERE movement_date >= '2025-01-01'
ORDER BY 
    store_id,
    movement_date;
