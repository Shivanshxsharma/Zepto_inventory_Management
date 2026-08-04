-- 01_load_data.sql
-- Loads the generated CSV datasets into the MySQL tables.
-- Make sure to run this script from the zepto-inventory-project root directory, e.g.:
-- mysql -u your_user -p < sql/01_load_data.sql

USE zepto_inventory;

-- Temporarily disable foreign key checks to speed up bulk loading
SET FOREIGN_KEY_CHECKS = 0;

-- Products
LOAD DATA LOCAL INFILE 'dataset/products.csv'
INTO TABLE products
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(sku_id, sku_name, category, mrp, unit_cost, unit_weight_grams, @is_perishable, shelf_life_days, demand_weight)
SET is_perishable = (@is_perishable = 'True');

-- Dark Stores
LOAD DATA LOCAL INFILE 'dataset/dark_stores.csv'
INTO TABLE dark_stores
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(store_id, store_name, city, zone, locality, latitude, longitude, capacity_units, opened_date);

-- Suppliers
LOAD DATA LOCAL INFILE 'dataset/suppliers.csv'
INTO TABLE suppliers
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(supplier_id, supplier_name, city, avg_lead_time_days);

-- Product Suppliers
LOAD DATA LOCAL INFILE 'dataset/product_suppliers.csv'
INTO TABLE product_suppliers
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(sku_id, supplier_id, cost_price);

-- Customers
LOAD DATA LOCAL INFILE 'dataset/customers.csv'
INTO TABLE customers
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(customer_id, customer_name, customer_email, customer_phone, zone, locality, signup_date);

-- Orders
LOAD DATA LOCAL INFILE 'dataset/orders.csv'
INTO TABLE orders
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(order_id, customer_id, store_id, order_timestamp, order_status, @delivery_time, order_date)
SET delivery_time_mins = NULLIF(@delivery_time, '');

-- Order Items
LOAD DATA LOCAL INFILE 'dataset/order_items.csv'
INTO TABLE order_items
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(order_item_id, order_id, sku_id, quantity, unit_price_at_sale, discount_pct, batch_id);

-- Purchase Orders
LOAD DATA LOCAL INFILE 'dataset/purchase_orders.csv'
INTO TABLE purchase_orders
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(batch_id, po_line_id, store_id, sku_id, supplier_id, order_date, expected_delivery_date, @actual_delivery, quantity_ordered, cost_price)
SET actual_delivery_date = NULLIF(@actual_delivery, '');

-- ML Forecasts
LOAD DATA LOCAL INFILE 'forecasting/ml_predictions.csv'
INTO TABLE fact_ml_forecasts
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(store_id, sku_id, snapshot_date, target_sold_qty, predicted_demand);

SET FOREIGN_KEY_CHECKS = 1;
