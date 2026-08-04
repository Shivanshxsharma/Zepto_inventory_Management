-- 04_wastage_log.sql
-- Calculates historical wastage by comparing purchased quantities 
-- against sold quantities for each specific batch, store, and SKU.

USE zepto_inventory;

-- Create the wastage log table
DROP TABLE IF EXISTS fact_wastage_log;
CREATE TABLE IF NOT EXISTS fact_wastage_log (
    batch_id INT,
    store_id INT,
    store_name VARCHAR(100),
    sku_id INT,
    sku_name VARCHAR(255),
    actual_delivery_date DATE,
    expiry_date DATE,
    quantity_purchased INT,
    quantity_sold INT,
    quantity_wasted INT,
    PRIMARY KEY (batch_id, store_id, sku_id)
);

-- Insert the calculated wastage data
INSERT INTO fact_wastage_log
WITH batch_sales AS (
    -- Calculate total quantity sold for each batch, store, and SKU
    SELECT 
        oi.batch_id,
        o.store_id,
        oi.sku_id,
        SUM(oi.quantity) AS total_quantity_sold
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY 
        oi.batch_id,
        o.store_id,
        oi.sku_id
),
batch_purchases AS (
    -- Calculate expiry dates and get purchased quantities
    SELECT 
        po.batch_id,
        po.store_id,
        ds.store_name,
        po.sku_id,
        p.sku_name,
        po.actual_delivery_date,
        DATE_ADD(po.actual_delivery_date, INTERVAL p.shelf_life_days DAY) AS expiry_date,
        SUM(po.quantity_ordered) AS quantity_purchased
    FROM purchase_orders po
    JOIN products p ON po.sku_id = p.sku_id
    JOIN dark_stores ds ON po.store_id = ds.store_id
    WHERE po.actual_delivery_date IS NOT NULL
    GROUP BY
        po.batch_id,
        po.store_id,
        ds.store_name,
        po.sku_id,
        p.sku_name,
        po.actual_delivery_date,
        p.shelf_life_days
)
SELECT 
    bp.batch_id,
    bp.store_id,
    bp.store_name,
    bp.sku_id,
    bp.sku_name,
    bp.actual_delivery_date,
    bp.expiry_date,
    bp.quantity_purchased,
    COALESCE(bs.total_quantity_sold, 0) AS quantity_sold,
    bp.quantity_purchased - COALESCE(bs.total_quantity_sold, 0) AS quantity_wasted
FROM batch_purchases bp
LEFT JOIN batch_sales bs 
    ON bp.batch_id = bs.batch_id 
    AND bp.store_id = bs.store_id 
    AND bp.sku_id = bs.sku_id
WHERE bp.expiry_date <= '2025-03-31'  
  AND (bp.quantity_purchased - COALESCE(bs.total_quantity_sold, 0)) > 0;

-- Performance indexes for wastage KPIs
CREATE INDEX idx_wastage_store ON fact_wastage_log(store_id);
CREATE INDEX idx_wastage_sku ON fact_wastage_log(sku_id);
