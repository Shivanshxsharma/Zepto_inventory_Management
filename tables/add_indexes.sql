USE zepto_inventory;

-- ==========================================
-- PERFORMANCE OPTIMIZATION (INDEXES)
-- ==========================================
-- These indexes are created AFTER data load
-- to utilize bulk-build algorithms instead of
-- slow row-by-row rebalancing.

CREATE INDEX idx_orders_status ON orders(order_status);
CREATE INDEX idx_orders_store ON orders(store_id);
CREATE INDEX idx_orders_timestamp ON orders(order_timestamp);
CREATE INDEX idx_orders_date_cov ON orders(order_status, store_id, order_date, order_id);

CREATE INDEX idx_order_items_sku ON order_items(sku_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_batch ON order_items(batch_id);
CREATE INDEX idx_order_items_sku_order ON order_items(sku_id, order_id);

CREATE INDEX idx_po_batch ON purchase_orders(batch_id);
CREATE INDEX idx_po_sku ON purchase_orders(sku_id);
CREATE INDEX idx_po_actual_delivery ON purchase_orders(actual_delivery_date);
