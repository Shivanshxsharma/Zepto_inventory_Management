-- ==============================================================================
-- View: view_reorder_points
-- Description: Calculates daily Safety Stock and Reorder Points purely in SQL
-- Dependencies: 
--   1. fact_ml_forecasts (Table loaded from Python predictions)
--   2. view_sales_velocity (For Z-Score)
--   3. product_suppliers & view_supplier_reliability (For Blended Lead Time & Lead Time StdDev)
-- ==============================================================================

CREATE OR REPLACE VIEW view_reorder_points AS
WITH ml_errors AS (
    -- Calculate forecast error and Sigma (standard deviation of demand) per store-sku dynamically
    SELECT 
        store_id,
        sku_id,
        snapshot_date,
        target_sold_qty,
        predicted_demand,
        COALESCE(STDDEV(target_sold_qty - predicted_demand) OVER (PARTITION BY store_id, sku_id), 0) AS sigma
    FROM fact_ml_forecasts
),
lead_times AS (
    -- Calculate expected lead time and lead time stddev by averaging the ACTUAL historical metrics 
    -- across all eligible suppliers for each SKU, using the supplier reliability view
    SELECT 
        ps.sku_id, 
        COALESCE(AVG(vsr.avg_actual_lead_time_days), 1) AS lead_time_avg,
        COALESCE(AVG(vsr.lead_time_stddev_days), 0) AS lead_time_stddev
    FROM product_suppliers ps
    JOIN view_supplier_reliability vsr ON ps.supplier_id = vsr.supplier_id
    GROUP BY ps.sku_id
),
velocity_z_scores AS (
    -- Map Store-Specific Classification to Z-Score
    SELECT 
        store_id, 
        sku_id, 
        classification,
        CASE classification
            WHEN 'Fast-moving' THEN 2.33
            WHEN 'Medium-moving' THEN 1.65
            WHEN 'Slow-moving' THEN 1.28
            ELSE 1.28
        END AS z_score
    FROM view_sales_velocity
)

SELECT 
    f.store_id,
    f.sku_id,
    f.snapshot_date,
    
    -- Inputs
    f.target_sold_qty,
    f.predicted_demand,
    f.sigma,
    v.classification AS velocity_class,
    v.z_score,
    lt.lead_time_avg,
    lt.lead_time_stddev,
    
    -- Safety Stock Calculation: Z * SQRT( (lead_time_avg * sigma^2) + (predicted_demand^2 * lead_time_stddev^2) )
    CEILING(
        v.z_score * SQRT(
            (lt.lead_time_avg * POWER(f.sigma, 2)) + 
            (POWER(f.predicted_demand, 2) * POWER(lt.lead_time_stddev, 2))
        )
    ) AS safety_stock,
    
    -- Reorder Point Calculation: (Demand * Lead Time) + Safety Stock
    CEILING(
        (f.predicted_demand * lt.lead_time_avg) + 
        (
            v.z_score * SQRT(
                (lt.lead_time_avg * POWER(f.sigma, 2)) + 
                (POWER(f.predicted_demand, 2) * POWER(lt.lead_time_stddev, 2))
            )
        )
    ) AS reorder_point

FROM ml_errors f
LEFT JOIN velocity_z_scores v ON f.store_id = v.store_id AND f.sku_id = v.sku_id
LEFT JOIN lead_times lt ON f.sku_id = lt.sku_id;
