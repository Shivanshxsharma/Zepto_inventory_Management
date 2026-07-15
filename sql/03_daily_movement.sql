-- 03_daily_movement.sql
-- Table to track daily movement (sales and purchases) for each store and SKU.

USE zepto_inventory;

-- Create the daily movement table
CREATE TABLE IF NOT EXISTS fact_daily_movement (
    store_id INT,
    store_name VARCHAR(100),
    movement_date DATE,
    sku_id INT,
    sku_name VARCHAR(255),
    total_quantity_sold INT,
    total_quantity_purchased INT,
    PRIMARY KEY (store_id, sku_id, movement_date)
);

-- Insert aggregated movement data combining sales and purchases
INSERT INTO fact_daily_movement
WITH daily_sales AS (
    SELECT 
        DATE(o.order_timestamp) AS movement_date,
        o.store_id,
        oi.sku_id,
        SUM(oi.quantity) AS quantity_sold
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY 
        DATE(o.order_timestamp),
        o.store_id,
        oi.sku_id
),
daily_purchases AS (
    SELECT 
        actual_delivery_date AS movement_date,
        store_id,
        sku_id,
        SUM(quantity_ordered) AS quantity_purchased
    FROM purchase_orders
    WHERE status = 'delivered' AND actual_delivery_date IS NOT NULL
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
        0 AS quantity_purchased
    FROM daily_sales
    UNION ALL
    SELECT 
        movement_date,
        store_id,
        sku_id,
        0 AS quantity_sold,
        quantity_purchased
    FROM daily_purchases
)
SELECT 
    cm.store_id,
    ds.store_name,
    cm.movement_date,
    cm.sku_id,
    p.sku_name,
    SUM(cm.quantity_sold) AS total_quantity_sold,
    SUM(cm.quantity_purchased) AS total_quantity_purchased
FROM combined_movement cm
JOIN dark_stores ds ON cm.store_id = ds.store_id
JOIN products p ON cm.sku_id = p.sku_id
GROUP BY 
    cm.store_id,
    ds.store_name,
    cm.movement_date,
    cm.sku_id,
    p.sku_name;
