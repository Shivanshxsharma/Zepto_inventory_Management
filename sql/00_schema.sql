-- 00_schema.sql
-- Create the base tables for the Zepto inventory project.
-- Run this before loading the data.

CREATE DATABASE IF NOT EXISTS zepto_inventory;
USE zepto_inventory;

CREATE TABLE IF NOT EXISTS products (
    sku_id INT PRIMARY KEY,
    sku_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    mrp DECIMAL(10, 2),
    unit_cost DECIMAL(10, 2),
    unit_weight_grams INT,
    is_perishable BOOLEAN,
    shelf_life_days INT,
    demand_weight INT
);

CREATE TABLE IF NOT EXISTS dark_stores (
    store_id INT PRIMARY KEY,
    store_name VARCHAR(100),
    city VARCHAR(50),
    zone VARCHAR(50),
    locality VARCHAR(100),
    latitude DECIMAL(9, 6),
    longitude DECIMAL(9, 6),
    capacity_units INT,
    opened_date DATE
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INT PRIMARY KEY,
    supplier_name VARCHAR(255),
    city VARCHAR(50),
    avg_lead_time_days INT
);

CREATE TABLE IF NOT EXISTS product_suppliers (
    sku_id INT,
    supplier_id INT,
    cost_price DECIMAL(10, 2),
    FOREIGN KEY (sku_id) REFERENCES products(sku_id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(255),
    customer_email VARCHAR(255),
    customer_phone VARCHAR(50),
    zone VARCHAR(50),
    locality VARCHAR(100),
    signup_date DATE
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INT PRIMARY KEY,
    customer_id INT,
    store_id INT,
    order_timestamp DATETIME,
    order_status VARCHAR(50),
    delivery_time_mins INT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (store_id) REFERENCES dark_stores(store_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INT PRIMARY KEY,
    order_id INT,
    sku_id INT,
    quantity INT,
    unit_price_at_sale DECIMAL(10, 2),
    discount_pct INT,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (sku_id) REFERENCES products(sku_id)
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    purchase_order_id INT PRIMARY KEY,
    store_id INT,
    supplier_id INT,
    sku_id INT,
    quantity_ordered INT,
    cost_price DECIMAL(10, 2),
    order_date DATE,
    expected_delivery_date DATE,
    actual_delivery_date DATE,
    status VARCHAR(50),
    FOREIGN KEY (store_id) REFERENCES dark_stores(store_id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
    FOREIGN KEY (sku_id) REFERENCES products(sku_id)
);

-- ==========================================
-- PERFORMANCE OPTIMIZATION (INDEXES)
-- ==========================================
-- These indexes drastically speed up aggregations 
-- and joins for large reporting queries.

CREATE INDEX idx_orders_status ON orders(order_status);
CREATE INDEX idx_orders_timestamp ON orders(order_timestamp);
CREATE INDEX idx_order_items_sku ON order_items(sku_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
