-- 02_daily_items_sold.sql
-- The most efficient way to handle "Items Sold" data in a Data Warehouse / Portfolio 
-- Project is to create an aggregated "Fact Table" (or Materialized View). 
-- This prevents the database from running a heavy 4-table join on 300k+ rows 
-- every time you refresh your BI dashboard.

USE zepto_inventory;

-- Create the summary table
CREATE TABLE IF NOT EXISTS fact_daily_sales (
    store_id INT,
    store_name VARCHAR(100),
    order_date DATE,
    sku_id INT,
    sku_name VARCHAR(255),
    total_quantity_sold INT,
    total_revenue DECIMAL(15, 2),
    PRIMARY KEY (store_id, sku_id, order_date)
);

-- Note on Pricing: 
-- In our python generator (04_orders.py), 'unit_price_at_sale' ALREADY 
-- has the discount applied to the MRP. 
-- So revenue is simply: SUM(quantity * unit_price_at_sale)

-- Insert the aggregated data for the current month
INSERT INTO fact_daily_sales
SELECT 
    ds.store_id,
    ds.store_name,
    DATE(o.order_timestamp) AS order_date,
    p.sku_id,
    p.sku_name,
    SUM(oi.quantity) AS total_quantity_sold,
    SUM(oi.quantity * oi.unit_price_at_sale) AS total_revenue
FROM orders o
-- Filter early to reduce join payload
JOIN order_items oi ON o.order_id = oi.order_id
JOIN dark_stores ds ON o.store_id = ds.store_id
JOIN products p     ON oi.sku_id = p.sku_id
WHERE o.order_status = 'delivered'
GROUP BY 
    ds.store_id,
    ds.store_name,
    DATE(o.order_timestamp),
    p.sku_id,
    p.sku_name;

-- Now, whenever you need your Items Sold data for analysis, 
-- you just query the aggregated table extremely fast:
-- SELECT * FROM fact_daily_sales WHERE order_date = '2025-01-15';
