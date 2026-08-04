-- ==============================================================================
-- KPI: Supplier Reliability
-- ==============================================================================
-- Formula Explanation:
-- Average Promised Lead Time = Average difference in days between order_date and expected_delivery_date
-- Average Actual Lead Time = Average difference in days between order_date and actual_delivery_date
-- Lead Time Deviation = Average Actual Lead Time - Average Promised Lead Time
-- On-Time Percentage = (Number of orders where actual delivery <= expected delivery / Total orders) * 100
-- Average Delay Days = For late orders only, the average difference between actual and expected delivery
-- ==============================================================================

-- FROM HERE THE VIEW CREATION STARTS
CREATE OR REPLACE VIEW view_supplier_reliability AS
SELECT
    po.supplier_id,
    s.supplier_name,
    COUNT(*) AS total_orders,
    ROUND(AVG(DATEDIFF(expected_delivery_date, order_date)), 2) AS avg_promised_lead_time_days,
    ROUND(AVG(DATEDIFF(actual_delivery_date, order_date)), 2) AS avg_actual_lead_time_days,
    ROUND(STDDEV(DATEDIFF(actual_delivery_date, order_date)), 2) AS lead_time_stddev_days,
    ROUND(
        AVG(DATEDIFF(actual_delivery_date, order_date))
        - AVG(DATEDIFF(expected_delivery_date, order_date))
    , 2) AS avg_lead_time_deviation_days,
    ROUND(
        SUM(CASE WHEN actual_delivery_date <= expected_delivery_date THEN 1 ELSE 0 END) * 100.0
        / COUNT(*)
    , 2) AS on_time_pct,
    ROUND(AVG(
        CASE WHEN actual_delivery_date > expected_delivery_date
        THEN DATEDIFF(actual_delivery_date, expected_delivery_date) END
    ), 2) AS avg_delay_days_when_late
FROM purchase_orders po
JOIN suppliers s ON po.supplier_id = s.supplier_id
GROUP BY po.supplier_id, s.supplier_name
ORDER BY on_time_pct ASC;
