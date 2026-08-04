-- ==============================================================================
-- KPI: Network Summary
-- ==============================================================================
-- Aggregates network-wide KPIs.
--
-- Total Revenue = SUM(unit_price_at_sale * quantity) for delivered orders
-- Total Stock Out Rate = (Total Stockout Days across all stores) / (Total SKU-Days across all stores) * 100
-- ==============================================================================

CREATE OR REPLACE VIEW view_network_summary AS
WITH network_revenue AS (
    SELECT
        ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN oi.unit_price_at_sale * oi.quantity ELSE 0 END), 2) AS total_network_revenue,
        ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN (oi.unit_price_at_sale - p.unit_cost) * oi.quantity ELSE 0 END), 2) AS total_network_profit
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.sku_id = p.sku_id
),
network_stockouts AS (
    SELECT
        ROUND(
            (SELECT COUNT(*) FROM view_stock_out_incidents) * 100.0 / 
            ((SELECT COUNT(DISTINCT CONCAT(store_id, '_', sku_id)) FROM fact_daily_movement) * 90)
        , 2) AS network_stockout_rate_pct
),
network_wastage AS (
    SELECT
        ROUND(
            COALESCE(SUM(fw.quantity_wasted), 0) * 100.0 
            / NULLIF(SUM(po.quantity_ordered), 0)
        , 2) AS network_wastage_pct
    FROM purchase_orders po
    LEFT JOIN fact_wastage_log fw 
        ON po.batch_id = fw.batch_id
        AND po.sku_id = fw.sku_id
),
network_turnover AS (
    SELECT
        ROUND(
            SUM(total_units_sold) * 1.0 / NULLIF(SUM(avg_inventory), 0)
        , 2) AS network_inventory_turnover_ratio,
        ROUND(
            90.0 / NULLIF(
                SUM(total_units_sold) * 1.0 / NULLIF(SUM(avg_inventory), 0)
            , 0)
        , 1) AS network_days_of_inventory_on_hand
    FROM view_inventory_turnover
)
SELECT
    nr.total_network_revenue,
    nr.total_network_profit,
    ns.network_stockout_rate_pct,
    nw.network_wastage_pct,
    nt.network_inventory_turnover_ratio,
    nt.network_days_of_inventory_on_hand
FROM network_revenue nr
CROSS JOIN network_stockouts ns
CROSS JOIN network_wastage nw
CROSS JOIN network_turnover nt;
