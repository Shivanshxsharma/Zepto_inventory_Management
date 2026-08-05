CREATE OR REPLACE VIEW view_store_movement AS
SELECT
    fm.store_id,
    fm.store_name,
    fm.movement_date,
    SUM(fm.total_sold_value)      AS sales_value,
    SUM(fm.total_purchased_value) AS purchase_value,
    SUM(COALESCE(inv.closing_stock, 0) * p.unit_cost) AS inventory_value,
    MAX(CASE WHEN inv.closing_stock = 0 THEN 1 ELSE 0 END) AS stockout_flag
FROM fact_daily_movement fm
LEFT JOIN view_inventory_snapshot inv
    ON fm.store_id = inv.store_id 
   AND fm.sku_id = inv.sku_id 
   AND fm.movement_date = inv.movement_date
JOIN products p ON fm.sku_id = p.sku_id
GROUP BY fm.store_id, fm.store_name, fm.movement_date;
