-- ==============================================================================
-- KPI: Wastage Information
-- ==============================================================================
-- Formula Explanation:
-- Total Quantity Purchased = Sum of all items bought for a specific batch/store/SKU
-- Total Quantity Sold = Sum of all items sold for that batch
-- Total Quantity Wasted = The difference (unsold stock that expired)
-- Wastage Percentage = (Total Quantity Wasted / Total Quantity Purchased) * 100
-- Wastage Value (Cost) = Total Quantity Wasted * Unit Cost (amount the store lost)
-- Wastage Value (MRP) = Total Quantity Wasted * MRP (potential revenue lost)
-- ==============================================================================

-- FROM HERE THE VIEW CREATION STARTS
CREATE OR REPLACE VIEW view_wastage_info AS
SELECT
    fw.store_id,
    fw.store_name,
    fw.sku_id,
    fw.sku_name,
    p.category,
    SUM(fw.quantity_purchased) AS total_quantity_purchased,
    SUM(fw.quantity_sold) AS total_quantity_sold,
    SUM(fw.quantity_wasted) AS total_quantity_wasted,

    ROUND(
        SUM(fw.quantity_wasted) * 100.0 / NULLIF(SUM(fw.quantity_purchased), 0)
    , 2) AS wastage_pct,

    p.unit_cost,
    ROUND(SUM(fw.quantity_wasted) * p.unit_cost, 2) AS wastage_value_cost,
    ROUND(SUM(fw.quantity_wasted) * p.mrp, 2) AS wastage_value_mrp_equivalent

FROM fact_wastage_log fw
JOIN products p ON fw.sku_id = p.sku_id
GROUP BY
    fw.store_id, fw.store_name, fw.sku_id, fw.sku_name, p.category, p.unit_cost, p.mrp
ORDER BY wastage_value_cost DESC;
