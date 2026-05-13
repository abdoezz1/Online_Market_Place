INSERT INTO users (username, email, password, first_name, last_name, is_staff, is_active)
VALUES
    ('ahmed_m',   'ahmed@mail.com',   '$2b$12$rZ5OkHi0qBxvcB3bpN.RhuFCvDRa.LAWLxwZ9bbonbZnSF69urCra', 'Ahmed',  'Mohamed', FALSE, TRUE),
    ('sara_k',    'sara@mail.com',    '$2b$12$QBElWtENFhbEw19LJqL8CeU9i/qMBj4.ffgxKxaZQd.LFzCqaBYAa', 'Sara',   'Kamal',   FALSE, TRUE),
    ('omar_h',    'omar@mail.com',    '$2b$12$FyTRPqnbylQ11sm0y1pC0uy8TTchkp1W9LJ3uEP8p66eB4L45SzO6', 'Omar',   'Hassan',  FALSE, TRUE),
    ('admin',     'admin@mail.com',   '$2b$12$DQ7xyChMz0b/68u8xg9bQu1TdKliey.c865cMH6x7/T9rnDgVIlla', 'Admin',  'User',    TRUE,  TRUE),
    ('nour_a',    'nour@mail.com',    '$2b$12$bSNGV4DLFl9nF2H4htVHI.q5MXet0YsmS92N7vgrtmAfa1b.WiPjq', 'Nour',   'Ali',     FALSE, TRUE);


INSERT INTO user_profiles (user_id, balance, created_at, updated_at)
VALUES
    (1, 1000.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (2, 1000.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (3, 1000.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (4, 1000.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    (5, 1000.00, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);


INSERT INTO categories (name)
VALUES
    ('Electronics'),
    ('Clothing'),
    ('Books'),
    ('Furniture'),
    ('Sports'),
    ('Toys'),
    ('Kitchen'),
    ('Automotive');


INSERT INTO items (name, price, description, quantity, for_sale, available_stock, average_rating, view_count, owned_by_id, category_id)
VALUES
    ('iPhone 13',          799.99, 'Apple iPhone 13 128GB',           5,  TRUE,  5,  4.80, 120, 1, 1),
    ('Samsung TV 55"',     499.99, 'Samsung 4K UHD Smart TV',         3,  TRUE,  3,  4.50, 85,  2, 1),
    ('Laptop Dell XPS',    999.99, 'Dell XPS 15 Intel i7',            2,  TRUE,  2,  4.70, 200, 3, 1),
    ('Wireless Headphones', 79.99, 'Noise cancelling headphones',     10, TRUE,  10, 4.20, 60,  1, 1),
    ('Men''s Jacket',       49.99, 'Winter jacket size L',            8,  TRUE,  8,  4.00, 40,  2, 2),
    ('Women''s Dress',      39.99, 'Floral summer dress size M',      6,  TRUE,  6,  4.30, 55,  3, 2),
    ('Running Shoes',       89.99, 'Nike Air Max size 42',            4,  TRUE,  4,  4.60, 90,  4, 2),
    ('T-Shirt Pack',        19.99, 'Pack of 3 cotton t-shirts',       15, TRUE,  15, 4.10, 30,  5, 2),
    ('Clean Code',          29.99, 'By Robert C. Martin',             7,  TRUE,  7,  4.90, 150, 1, 3),
    ('The Pragmatic Programmer', 34.99, 'By David Thomas',            5,  TRUE,  5,  4.80, 130, 2, 3),
    ('Design Patterns',    39.99, 'Gang of Four book',                4,  TRUE,  4,  4.70, 110, 3, 3),
    ('Office Desk',        199.99, 'Wooden office desk 120cm',        2,  TRUE,  2,  4.40, 70,  4, 4),
    ('Bookshelf',           89.99, '5-tier wooden bookshelf',         3,  TRUE,  3,  4.20, 45,  5, 4),
    ('Gaming Chair',       249.99, 'Ergonomic gaming chair',          2,  TRUE,  2,  4.60, 95,  1, 4),
    ('Yoga Mat',            24.99, 'Non-slip 6mm yoga mat',           10, TRUE,  10, 4.30, 50,  2, 5),
    ('Dumbbells Set',       59.99, '20kg adjustable dumbbells',       5,  TRUE,  5,  4.50, 75,  3, 5),
    ('Football',            19.99, 'FIFA approved size 5',            8,  TRUE,  8,  4.10, 35,  4, 5),
    ('LEGO City Set',       49.99, '500 pieces city builder',         6,  TRUE,  6,  4.70, 80,  5, 6),
    ('Coffee Maker',        39.99, '12-cup programmable coffee maker',4,  TRUE,  4,  4.40, 65,  1, 7),
    ('Air Fryer',           69.99, '5L digital air fryer',            3,  TRUE,  3,  4.60, 100, 2, 7),
    ('Car Phone Mount',     14.99, 'Universal dashboard mount',       12, TRUE,  12, 4.00, 25,  3, 8),
    ('Dash Cam',            59.99, '1080p front and rear dash cam',   5,  TRUE,  5,  4.30, 55,  4, 8);

UPDATE items SET image = '/static/images/default-product-image.jpg' WHERE image IS NULL OR image = '';



INSERT INTO transactions (buyer_id, seller_id, product_id, quantity, total_price, status)
VALUES
    (1, 2, 5,  1, 49.99,  'completed'),
    (2, 3, 9,  1, 29.99,  'completed'),
    (3, 1, 1,  1, 799.99, 'pending'),
    (4, 5, 15, 2, 49.98,  'completed'),
    (5, 1, 19, 1, 39.99,  'cancelled');



INSERT INTO deposits (amount, status, user_id)
VALUES
    (200.00, 'completed', 1),
    (500.00, 'completed', 2),
    (150.00, 'pending',   3),
    (300.00, 'completed', 5),
    (50.00,  'failed',    4);

INSERT INTO api_clients (name, api_key, is_active, user_profile_id)
VALUES
    ('Mobile App Client',     'ak_mobile_a1b2c3d4e5f6g7h8i9j0', TRUE, 1),
    ('Third Party Dashboard', 'ak_dash_z9y8x7w6v5u4t3s2r1q0',  TRUE, 2);