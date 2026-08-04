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
    -- Calculate expected lead time and lead time stddev by using WEIGHTED AVERAGES
    -- based on the number of orders from each supplier for that store-sku
    SELECT 
        store_id,
        sku_id, 
        COALESCE(SUM(avg_lead_time_days * total_orders) / NULLIF(SUM(total_orders), 0), 1) AS lead_time_avg,
        COALESCE(SUM(lead_time_stddev_days * total_orders) / NULLIF(SUM(total_orders), 0), 0) AS lead_time_stddev
    FROM view_store_sku_supplier_leadtime
    GROUP BY store_id, sku_id
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
    COALESCE(lt.lead_time_avg, 1) AS lead_time_avg,
    COALESCE(lt.lead_time_stddev, 0) AS lead_time_stddev,
    
    -- Safety Stock Calculation: Z * SQRT( (lead_time_avg * sigma^2) + (predicted_demand^2 * lead_time_stddev^2) )
    CEILING(
        v.z_score * SQRT(
            (COALESCE(lt.lead_time_avg, 1) * POWER(f.sigma, 2)) + 
            (POWER(f.predicted_demand, 2) * POWER(COALESCE(lt.lead_time_stddev, 0), 2))
        )
    ) AS safety_stock,
    
    -- Reorder Point Calculation: (Demand * Lead Time) + Safety Stock
    CEILING(
        (f.predicted_demand * COALESCE(lt.lead_time_avg, 1)) + 
        (
            v.z_score * SQRT(
                (COALESCE(lt.lead_time_avg, 1) * POWER(f.sigma, 2)) + 
                (POWER(f.predicted_demand, 2) * POWER(COALESCE(lt.lead_time_stddev, 0), 2))
            )
        )
    ) AS reorder_point

FROM ml_errors f
LEFT JOIN velocity_z_scores v ON f.store_id = v.store_id AND f.sku_id = v.sku_id
LEFT JOIN lead_times lt ON f.store_id = lt.store_id AND f.sku_id = lt.sku_id;
