CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(150) UNIQUE NOT NULL,
    email       VARCHAR(254) UNIQUE NOT NULL,
    password    TEXT NOT NULL,
    first_name  VARCHAR(100),
    last_name   VARCHAR(100),
    is_staff    BOOLEAN DEFAULT FALSE,
    is_active   BOOLEAN DEFAULT TRUE,
    date_joined TIMESTAMP DEFAULT NOW()
);


CREATE TABLE categories (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE contact_messages (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(150) NOT NULL,
    email      VARCHAR(254) NOT NULL,
    message    TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_profiles (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    photo         TEXT,
    bio           TEXT,
    phone         VARCHAR(20),
    address       TEXT,
    date_of_birth DATE,
    age           INTEGER,
    balance       NUMERIC(12, 2) DEFAULT 0.00,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sessions (
    id          SERIAL PRIMARY KEY,
    session_key VARCHAR(64) UNIQUE NOT NULL,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TIMESTAMP NOT NULL
);

CREATE TABLE api_clients (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(150) NOT NULL,
    api_key         VARCHAR(64) UNIQUE NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    user_profile_id INTEGER REFERENCES user_profiles(id) ON DELETE SET NULL
);


CREATE TABLE items (
    id                SERIAL PRIMARY KEY,
    name              VARCHAR(255) NOT NULL,
    price             NUMERIC(12, 2) NOT NULL,
    description       TEXT,
    image             TEXT,
    quantity          INTEGER DEFAULT 0,
    for_sale          BOOLEAN DEFAULT FALSE,
    available_stock   INTEGER DEFAULT 0,
    advertise         BOOLEAN DEFAULT FALSE,
    quantity_advertise INTEGER DEFAULT 0,
    average_rating    NUMERIC(3, 2) DEFAULT 0.00,
    view_count        INTEGER DEFAULT 0,
    created_at        TIMESTAMP DEFAULT NOW(),
    owned_by_id       INTEGER REFERENCES user_profiles(id) ON DELETE SET NULL,
    category_id       INTEGER REFERENCES categories(id) ON DELETE SET NULL
);

CREATE TABLE wishlist (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, product_id)
);


CREATE TABLE orders (
    id         SERIAL PRIMARY KEY,
    buyer_id   INTEGER REFERENCES user_profiles(id) ON DELETE SET NULL,
    seller_id  INTEGER REFERENCES user_profiles(id) ON DELETE SET NULL,
    product_id INTEGER REFERENCES items(id) ON DELETE SET NULL,
    quantity   INTEGER NOT NULL
);

CREATE TABLE transactions (
    transaction_id SERIAL PRIMARY KEY,
    buyer_id       INTEGER REFERENCES user_profiles(id) ON DELETE SET NULL,
    seller_id      INTEGER REFERENCES user_profiles(id) ON DELETE SET NULL,
    product_id     INTEGER REFERENCES items(id) ON DELETE SET NULL,
    quantity       INTEGER NOT NULL,
    total_price    NUMERIC(12, 2) NOT NULL,
    status         VARCHAR(50) DEFAULT 'pending',
    date           TIMESTAMP DEFAULT NOW()
);


CREATE TABLE deposits (
    id             SERIAL PRIMARY KEY,
    amount         NUMERIC(12, 2) NOT NULL,
    status         VARCHAR(50) DEFAULT 'pending',
    transaction_id INTEGER REFERENCES transactions(transaction_id) ON DELETE SET NULL,
    date           TIMESTAMP DEFAULT NOW(),
    user_id        INTEGER REFERENCES user_profiles(id) ON DELETE SET NULL
);

CREATE TABLE payments (
    id           SERIAL PRIMARY KEY,
    payment_date TIMESTAMP DEFAULT NOW(),
    is_successful BOOLEAN DEFAULT FALSE,
    buyer_id     INTEGER REFERENCES user_profiles(id) ON DELETE SET NULL,
    seller_id    INTEGER REFERENCES user_profiles(id) ON DELETE SET NULL,
    product_id   INTEGER REFERENCES items(id) ON DELETE SET NULL,
    quantity     INTEGER NOT NULL,
    total_price  NUMERIC(12, 2) NOT NULL,
    order_id     INTEGER REFERENCES orders(id) ON DELETE SET NULL
);


CREATE TABLE reviews (
    id             SERIAL PRIMARY KEY,
    transaction_id INTEGER REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    user_id        INTEGER REFERENCES user_profiles(id) ON DELETE SET NULL,
    product_id     INTEGER REFERENCES items(id) ON DELETE SET NULL,
    rating         NUMERIC(3, 2) NOT NULL,
    comment        TEXT,
    created_at     TIMESTAMP DEFAULT NOW(),
    updated_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE direct_messages (
    id          SERIAL PRIMARY KEY,
    sender_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    receiver_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    body        TEXT NOT NULL,
    timestamp   TIMESTAMP DEFAULT NOW(),
    is_read     BOOLEAN DEFAULT FALSE
);