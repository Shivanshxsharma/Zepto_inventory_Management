-- 03_daily_movement.sql
-- Table to track daily movement (sales and purchases) for each store and SKU.

USE zepto_inventory;

-- Create the daily movement table
DROP TABLE IF EXISTS fact_daily_movement;
CREATE TABLE IF NOT EXISTS fact_daily_movement (
    store_id INT,
    store_name VARCHAR(100),
    movement_date DATE,
    sku_id INT,
    sku_name VARCHAR(255),
    total_quantity_sold INT,
    total_sold_value DECIMAL(12, 2),
    total_quantity_purchased INT,
    total_purchased_value DECIMAL(12, 2),
    PRIMARY KEY (movement_date, store_id, sku_id)
);

-- Insert aggregated movement data combining sales and purchases
INSERT INTO fact_daily_movement
WITH daily_sales AS (
    SELECT 
        o.order_date AS movement_date,
        o.store_id,
        oi.sku_id,
        SUM(oi.quantity) AS quantity_sold,
        SUM(oi.quantity * oi.unit_price_at_sale) AS sold_value
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY 
        o.order_date,
        o.store_id,
        oi.sku_id
),
daily_purchases AS (
    SELECT 
        actual_delivery_date AS movement_date,
        store_id,
        sku_id,
        SUM(quantity_ordered) AS quantity_purchased,
        SUM(quantity_ordered * cost_price) AS purchased_value
    FROM purchase_orders
    WHERE actual_delivery_date IS NOT NULL
    GROUP BY 
        actual_delivery_date,
        store_id,
        sku_id
),
combined_movement AS (
    SELECT 
        movement_date,
        store_id,
        sku_id,
        quantity_sold,
        sold_value,
        0 AS quantity_purchased,
        0 AS purchased_value
    FROM daily_sales
    UNION ALL
    SELECT 
        movement_date,
        store_id,
        sku_id,
        0 AS quantity_sold,
        0 AS sold_value,
        quantity_purchased,
        purchased_value
    FROM daily_purchases
)
SELECT 
    cm.store_id,
    ds.store_name,
    cm.movement_date,
    cm.sku_id,
    p.sku_name,
    SUM(cm.quantity_sold) AS total_quantity_sold,
    ROUND(SUM(cm.sold_value), 2) AS total_sold_value,
    SUM(cm.quantity_purchased) AS total_quantity_purchased,
    ROUND(SUM(cm.purchased_value), 2) AS total_purchased_value
FROM combined_movement cm
JOIN dark_stores ds ON cm.store_id = ds.store_id
JOIN products p ON cm.sku_id = p.sku_id
GROUP BY 
    cm.store_id,
    ds.store_name,
    cm.movement_date,
    cm.sku_id,
    p.sku_name
ORDER BY 
     cm.movement_date;

-- Performance index for window functions
CREATE INDEX idx_snapshot_store_sku_date ON fact_daily_movement(store_id, sku_id, movement_date);
