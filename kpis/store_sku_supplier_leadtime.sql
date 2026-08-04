CREATE OR REPLACE VIEW view_store_sku_supplier_leadtime AS
SELECT
    store_id,
    sku_id,
    supplier_id,
    COUNT(*) AS total_orders,
    AVG(DATEDIFF(actual_delivery_date, order_date)) AS avg_lead_time_days,
    STDDEV(DATEDIFF(actual_delivery_date, order_date)) AS lead_time_stddev_days
FROM purchase_orders
WHERE actual_delivery_date IS NOT NULL
GROUP BY store_id, sku_id, supplier_id;
