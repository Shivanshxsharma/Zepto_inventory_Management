-- ==============================================================================
-- KPI: Store Performances
-- ==============================================================================
-- Aggregates revenue, cancellation rate, and delivery speed per store.
--
-- Total Revenue       = SUM(unit_price_at_sale * quantity) for delivered orders
-- Cancellation Rate   = (Cancelled Orders / Total Orders) * 100
-- Avg Delivery Time   = AVG(delivery_time_mins) for delivered orders
-- On-time Restock   = (On-time Purchase Orders / Total Purchase Orders) * 100
-- Wastage %         = (Total Wasted / Total Purchased) * 100
-- Wastage Value     = SUM(Wasted Quantity * Unit Cost)
-- Sales Velocity    = SUM(sales_velocity) across all SKUs in the store
-- Turnover & DOH    = Aggregated from view_inventory_turnover per store
-- Stockout Rate     = (Stockout Days / Total SKU-Days) * 100
-- ==============================================================================

-- FROM HERE THE VIEW CREATION STARTS
CREATE OR REPLACE VIEW view_store_performances AS
WITH store_orders AS (
    SELECT
        o.store_id,
        COUNT(DISTINCT o.order_id) AS total_orders,
        COUNT(DISTINCT CASE WHEN o.order_status = 'cancelled' THEN o.order_id END) AS cancelled_orders,
        COUNT(DISTINCT CASE WHEN o.order_status = 'delivered' THEN o.order_id END) AS delivered_orders,
        ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN oi.unit_price_at_sale * oi.quantity ELSE 0 END), 2) AS total_revenue,
        ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN (oi.unit_price_at_sale - p.unit_cost) * oi.quantity ELSE 0 END), 2) AS gross_profit,
        ROUND(
            COUNT(DISTINCT CASE WHEN o.order_status = 'cancelled' THEN o.order_id END) * 100.0 /
            NULLIF(COUNT(DISTINCT o.order_id), 0)
        , 2) AS cancellation_rate_pct,
        ROUND(AVG(CASE WHEN o.order_status = 'delivered' THEN o.delivery_time_mins END), 1) AS avg_delivery_time_mins
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.sku_id = p.sku_id
    GROUP BY o.store_id
),
store_restocks AS (
    SELECT
        store_id,
        COUNT(po_line_id) AS total_restocks,
        SUM(CASE WHEN actual_delivery_date <= expected_delivery_date THEN 1 ELSE 0 END) AS on_time_restocks,
        ROUND(
            SUM(CASE WHEN actual_delivery_date <= expected_delivery_date THEN 1 ELSE 0 END) * 100.0 /
            NULLIF(COUNT(po_line_id), 0)
        , 2) AS on_time_restock_pct
    FROM purchase_orders
    GROUP BY store_id
),
store_wastage AS (
    SELECT
        po.store_id,
        ROUND(
            COALESCE(SUM(fw.quantity_wasted), 0) * 100.0 
            / NULLIF(SUM(po.quantity_ordered), 0)
        , 2) AS wastage_pct,
        ROUND(COALESCE(SUM(fw.quantity_wasted * p.unit_cost), 0), 2) AS wastage_value
    FROM purchase_orders po
    JOIN products p ON po.sku_id = p.sku_id
    LEFT JOIN fact_wastage_log fw 
        ON po.batch_id = fw.batch_id
        AND po.sku_id = fw.sku_id
    GROUP BY po.store_id
),
store_velocity AS (
    SELECT
        store_id,
        ROUND(SUM(sales_velocity), 2) AS store_sales_velocity
    FROM view_sales_velocity
    GROUP BY store_id
),
store_top_category AS (
    SELECT
        store_id,
        category AS top_performing_category
    FROM (
        SELECT
            store_id,
            category,
            ROW_NUMBER() OVER(PARTITION BY store_id ORDER BY SUM(sales_velocity) DESC) as rn
        FROM view_sales_velocity
        GROUP BY store_id, category
    ) sub
    WHERE rn = 1
),
store_turnover AS (
    SELECT
        store_id,
        ROUND(
            SUM(total_units_sold) * 1.0 / NULLIF(SUM(avg_inventory), 0)
        , 2) AS store_inventory_turnover_ratio,
        ROUND(
            90.0 / NULLIF(
                SUM(total_units_sold) * 1.0 / NULLIF(SUM(avg_inventory), 0)
            , 0)
        , 1) AS store_days_of_inventory_on_hand
    FROM view_inventory_turnover
    GROUP BY store_id
),
store_stockouts AS (
    SELECT
        v.store_id,
        ROUND(COUNT(*) * 100.0 / ((SELECT COUNT(DISTINCT sku_id) FROM fact_daily_movement fdm WHERE fdm.store_id = v.store_id) * 90), 2) AS stockout_rate_pct
    FROM view_stock_out_incidents v
    GROUP BY v.store_id
)
SELECT
    ds.store_id,
    ds.store_name,
    ds.zone,
    so.total_orders,
    so.delivered_orders,
    so.cancelled_orders,
    so.total_revenue,
    so.gross_profit,
    so.cancellation_rate_pct,
    so.avg_delivery_time_mins,
    sr.on_time_restock_pct,
    sw.wastage_pct,
    sw.wastage_value,
    sv.store_sales_velocity,
    stc.top_performing_category,
    st.store_inventory_turnover_ratio,
    st.store_days_of_inventory_on_hand,
    sso.stockout_rate_pct
FROM dark_stores ds
JOIN store_orders so ON ds.store_id = so.store_id
LEFT JOIN store_restocks sr ON ds.store_id = sr.store_id
LEFT JOIN store_wastage sw ON ds.store_id = sw.store_id
LEFT JOIN store_velocity sv ON ds.store_id = sv.store_id
LEFT JOIN store_top_category stc ON ds.store_id = stc.store_id
LEFT JOIN store_turnover st ON ds.store_id = st.store_id
LEFT JOIN store_stockouts sso ON ds.store_id = sso.store_id
ORDER BY so.total_revenue DESC;
