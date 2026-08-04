USE zepto_inventory;

-- ==============================================================================
-- STEP 1: Base grid -- FIXED to guarantee one row per (store_id, sku_id, date)
-- ==============================================================================
-- Problem this fixes: view_inventory_snapshot is built from movement data
-- (fact_daily_movement-style UNION ALL + GROUP BY), which only contains rows
-- for days with actual sale or purchase activity -- NOT a complete day-by-day
-- grid. Days with zero sales are silently missing, not present as sold_qty=0.
-- This breaks LAG()/rolling window functions, since they assume consecutive
-- rows are consecutive DAYS -- with gaps, LAG(1) silently pulls the last
-- EXISTING row (which could be several real days earlier), not literally
-- "yesterday".
--
-- Fix: explicitly build the full (store x sku x date) grid first, then
-- LEFT JOIN the sparse source onto it and COALESCE missing sold_qty to 0.
-- This is safe regardless of whether the source was already complete or not.
-- ==============================================================================
CREATE OR REPLACE VIEW view_forecast_base AS
SELECT
    g.store_id,
    g.sku_id,
    g.snapshot_date,
    COALESCE(v.total_quantity_sold, 0) AS sold_qty
FROM (
    SELECT ds.store_id, p.sku_id, d.snapshot_date
    FROM dark_stores ds
    CROSS JOIN products p
    CROSS JOIN (
        SELECT DISTINCT movement_date AS snapshot_date
        FROM view_inventory_snapshot
        WHERE movement_date >= '2025-01-01'
    ) d
) g
LEFT JOIN view_inventory_snapshot v
    ON g.store_id = v.store_id
   AND g.sku_id = v.sku_id
   AND g.snapshot_date = v.movement_date;


-- ==============================================================================
-- STEP 2: Full feature table
-- ==============================================================================
CREATE OR REPLACE VIEW view_forecast_features AS
SELECT
    b.store_id,
    b.sku_id,
    b.snapshot_date,

    -- CALENDAR FEATURES
    DAYOFWEEK(b.snapshot_date) AS day_of_week,
    CASE WHEN DAYOFWEEK(b.snapshot_date) IN (1,7) THEN 1 ELSE 0 END AS is_weekend,
    DAY(b.snapshot_date) AS day_of_month,

    -- LAG FEATURES (now correctly "N days ago" since the grid has no gaps)
    LAG(b.sold_qty, 1) OVER (
        PARTITION BY b.store_id, b.sku_id ORDER BY b.snapshot_date
    ) AS sales_lag_1,
    LAG(b.sold_qty, 7) OVER (
        PARTITION BY b.store_id, b.sku_id ORDER BY b.snapshot_date
    ) AS sales_lag_7,
    LAG(b.sold_qty, 28) OVER (
        PARTITION BY b.store_id, b.sku_id ORDER BY b.snapshot_date
    ) AS sales_lag_28,

    -- ROLLING FEATURES (trailing 7 days, excluding current day -- no leakage)
    AVG(b.sold_qty) OVER (
        PARTITION BY b.store_id, b.sku_id ORDER BY b.snapshot_date
        ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
    ) AS rolling_7day_avg,
    STDDEV(b.sold_qty) OVER (
        PARTITION BY b.store_id, b.sku_id ORDER BY b.snapshot_date
        ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
    ) AS rolling_7day_stddev,

    -- STATIC FEATURES
    p.category,
    ds.zone,
    ds.capacity_units,
    p.unit_cost,
    p.mrp,

    -- TARGET
    b.sold_qty AS target_sold_qty

FROM view_forecast_base b
JOIN products p    ON b.sku_id  = p.sku_id
JOIN dark_stores ds ON b.store_id = ds.store_id;


-- ==============================================================================
-- STEP 3: Clean view -- drop rows without full history yet
-- ==============================================================================
CREATE OR REPLACE VIEW view_forecast_features_clean AS
SELECT *
FROM view_forecast_features
WHERE sales_lag_28 IS NOT NULL
  AND rolling_7day_avg IS NOT NULL;

