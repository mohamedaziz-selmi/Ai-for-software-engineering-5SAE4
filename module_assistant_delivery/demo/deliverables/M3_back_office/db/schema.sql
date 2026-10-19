-- PostgreSQL schema additions for M3 (staff back-office).

CREATE TABLE staff_accounts (
    id            SERIAL PRIMARY KEY,
    shop_id       INTEGER NOT NULL REFERENCES shops(id),
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,              -- Argon2id
    totp_secret   TEXT NOT NULL,              -- two-factor authentication is mandatory for staff
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE orders ADD COLUMN status TEXT NOT NULL DEFAULT 'preparing'
    CHECK (status IN ('preparing', 'ready', 'collected', 'cancelled'));

CREATE INDEX orders_shop_slot ON orders (shop_id, slot_start);
