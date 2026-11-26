CREATE DATABASE shopping_orders;
SELECT current_database();
SELECT datname FROM pg_database ORDER BY datname;

/* ---------- Schemas ---------- */
CREATE SCHEMA IF NOT EXISTS customer;
CREATE SCHEMA IF NOT EXISTS products;
CREATE SCHEMA IF NOT EXISTS orders;


/* ============================================================
   customer.customer_info  - who the customers are
   ============================================================ */
CREATE TABLE customer.customer_info (
    customer_id    INTEGER GENERATED ALWAYS AS IDENTITY,
    first_name     VARCHAR(50)   NOT NULL,
    last_name      VARCHAR(50)   NOT NULL,
    phone_number   VARCHAR(20),                     -- text, not number: keeps +91 and leading zeros
    email          VARCHAR(255)  NOT NULL,
    address_line1  VARCHAR(150),
    address_line2  VARCHAR(150),
    city           VARCHAR(80),
    state          VARCHAR(80),
    postal_code    VARCHAR(12),
    country        VARCHAR(60),
    created_at     TIMESTAMP(0)  NOT NULL DEFAULT now(),
    CONSTRAINT pk_customer_info PRIMARY KEY (customer_id),
    CONSTRAINT uq_customer_email UNIQUE (email)
);

/* ============================================================
   products.product  - product catalogue
   ============================================================ */
CREATE TABLE products.product (
    product_id        INTEGER GENERATED ALWAYS AS IDENTITY,
    product_name      VARCHAR(150)   NOT NULL,
    category          VARCHAR(80),
    description       VARCHAR(500),
    price             NUMERIC(10,2)  NOT NULL,      -- NUMERIC, never FLOAT, for money
    discounted_price  NUMERIC(10,2),                -- NULL = not on discount
    is_active         BOOLEAN        NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMP(0)   NOT NULL DEFAULT now(),
    CONSTRAINT pk_product PRIMARY KEY (product_id),
    CONSTRAINT ck_product_price CHECK (price >= 0),
    CONSTRAINT ck_product_discount CHECK (discounted_price IS NULL OR (discounted_price >= 0 AND discounted_price <= price))
);

/* ============================================================
   customer.customer_order  - order HEADER (who ordered, when)
   ============================================================ */
CREATE TABLE customer.customer_order (
    order_id      INTEGER GENERATED ALWAYS AS IDENTITY,
    customer_id   INTEGER      NOT NULL,
    order_date    TIMESTAMP(0) NOT NULL DEFAULT now(),
    order_status  VARCHAR(20)  NOT NULL DEFAULT 'Pending',
    CONSTRAINT pk_customer_order PRIMARY KEY (order_id),
    CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customer.customer_info (customer_id),
    CONSTRAINT ck_order_status CHECK (order_status IN ('Pending','Shipped','Delivered','Cancelled'))
);
CREATE INDEX ix_customer_order_customer ON customer.customer_order (customer_id);
CREATE INDEX ix_customer_order_date     ON customer.customer_order (order_date);

/* ============================================================
   orders.purchase_orders  - order LINE ITEMS (what was bought)
   ============================================================ */
CREATE TABLE orders.purchase_orders (
    purchase_order_id  INTEGER GENERATED ALWAYS AS IDENTITY,
    order_id           INTEGER        NOT NULL,
    product_id         INTEGER        NOT NULL,
    quantity           INTEGER        NOT NULL,
    unit_price         NUMERIC(10,2)  NOT NULL,     -- price actually charged at order time (snapshot)
    line_total         NUMERIC(12,2)  GENERATED ALWAYS AS (quantity * unit_price) STORED,
    CONSTRAINT pk_purchase_orders PRIMARY KEY (purchase_order_id),
    CONSTRAINT fk_po_order   FOREIGN KEY (order_id)   REFERENCES customer.customer_order (order_id),
    CONSTRAINT fk_po_product FOREIGN KEY (product_id) REFERENCES products.product (product_id),
    CONSTRAINT uq_po_order_product UNIQUE (order_id, product_id),
    CONSTRAINT ck_po_quantity CHECK (quantity > 0),
    CONSTRAINT ck_po_unit_price CHECK (unit_price >= 0)
);
CREATE INDEX ix_po_product ON orders.purchase_orders (product_id);

/* ============================================================
   orders.vw_daily_orders  - "daily orders" as a view, not a column
   ============================================================ */
CREATE VIEW orders.vw_daily_orders AS
SELECT  CAST(o.order_date AS DATE)   AS order_day,
        COUNT(DISTINCT o.order_id)   AS total_orders,
        SUM(p.quantity)              AS units_sold,
        SUM(p.line_total)            AS revenue
FROM    customer.customer_order o
JOIN    orders.purchase_orders  p ON p.order_id = o.order_id
GROUP BY CAST(o.order_date AS DATE);

/* ============================================================
   Sample data
   ============================================================ */
INSERT INTO customer.customer_info
    (first_name, last_name, phone_number, email, address_line1, city, state, postal_code, country)
VALUES
 ('Aarav',  'Sharma', '+91-9876500001', 'aarav.sharma@example.com', '12 MG Road',       'Bengaluru', 'Karnataka',   '560001', 'India'),
 ('Priya',  'Nair',   '+91-9876500002', 'priya.nair@example.com',   '45 Anna Salai',    'Chennai',   'Tamil Nadu',  '600002', 'India'),
 ('Rohan',  'Mehta',  '+91-9876500003', 'rohan.mehta@example.com',  '8 Marine Drive',   'Mumbai',    'Maharashtra', '400020', 'India'),
 ('Ananya', 'Iyer',   '+91-9876500004', 'ananya.iyer@example.com',  '21 T Nagar',       'Chennai',   'Tamil Nadu',  '600017', 'India'),
 ('Karthik','Raj',    '+91-9876500005', 'karthik.raj@example.com',  '77 Jubilee Hills', 'Hyderabad', 'Telangana',   '500033', 'India');

INSERT INTO products.product (product_name, category, price, discounted_price)
VALUES
 ('Wireless Mouse',              'Accessories',   799.00,   649.00),
 ('Mechanical Keyboard',         'Accessories',  3499.00,  2999.00),
 ('USB-C Hub',                   'Accessories',  1999.00,    NULL),
 ('27-inch Monitor',             'Electronics', 15999.00, 14499.00),
 ('Laptop Stand',                'Accessories',  1299.00,   999.00),
 ('Noise Cancelling Headphones', 'Audio',        7999.00,  6499.00);

INSERT INTO customer.customer_order (customer_id, order_date, order_status)
VALUES
 (1, '2026-11-18 10:15:00', 'Delivered'),
 (2, '2026-11-18 14:40:00', 'Delivered'),
 (3, '2026-11-19 09:05:00', 'Delivered'),
 (1, '2026-11-21 18:20:00', 'Shipped'),
 (4, '2026-11-22 11:00:00', 'Pending'),
 (5, '2026-11-22 16:45:00', 'Pending'),
 (2, '2026-11-23 08:30:00', 'Pending');

INSERT INTO orders.purchase_orders (order_id, product_id, quantity, unit_price)
VALUES
 (1, 1, 1,   649.00), (1, 5, 1,   999.00),
 (2, 6, 1,  6499.00),
 (3, 2, 1,  2999.00), (3, 3, 2,  1999.00),
 (4, 4, 1, 14499.00),
 (5, 1, 2,   649.00),
 (6, 5, 1,   999.00), (6, 3, 1,  1999.00),
 (7, 6, 1,  6499.00), (7, 1, 1,   649.00);

/* ============================================================
   Sample queries to test your AI agent
   ============================================================ */

-- 1. When was the last order placed?
SELECT MAX(order_date) AS last_order_date FROM customer.customer_order;

-- 2. Daily orders and revenue
SELECT * FROM orders.vw_daily_orders ORDER BY order_day;

-- 3. Top customers by total spend
SELECT c.first_name, c.last_name, SUM(p.line_total) AS total_spent
FROM customer.customer_info c
JOIN customer.customer_order o ON o.customer_id = c.customer_id
JOIN orders.purchase_orders  p ON p.order_id = o.order_id
GROUP BY c.first_name, c.last_name
ORDER BY total_spent DESC
LIMIT 3;

-- 4. Best-selling products by units
SELECT pr.product_name, SUM(p.quantity) AS units_sold
FROM orders.purchase_orders p
JOIN products.product pr ON pr.product_id = p.product_id
GROUP BY pr.product_name
ORDER BY units_sold DESC;

-- 5. Full order details with customer and product names
SELECT o.order_id, o.order_date, c.first_name || ' ' || c.last_name AS customer,
       pr.product_name, p.quantity, p.unit_price, p.line_total
FROM customer.customer_order o
JOIN customer.customer_info  c  ON c.customer_id = o.customer_id
JOIN orders.purchase_orders  p  ON p.order_id = o.order_id
JOIN products.product        pr ON pr.product_id = p.product_id
ORDER BY o.order_id;

select * from customer.customer_info limit 5;