CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role VARCHAR UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_verified BOOLEAN DEFAULT false,
    role_id UUID REFERENCES roles(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS company_games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game VARCHAR UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID REFERENCES company_games(id) ON DELETE SET NULL,
    type VARCHAR NOT NULL,
    price_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    is_active BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES subscription_plans(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    active_until DATE DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS promocodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR UNIQUE NOT NULL,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('pending', 'paid', 'failed', 'cancelled')),
    robokassa_invoice_id VARCHAR UNIQUE NOT NULL,
    idempotency_key VARCHAR UNIQUE NOT NULL,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS source_payment_id UUID REFERENCES payments(id) ON DELETE SET NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_subscriptions_permanent_user_plan
    ON subscriptions (user_id, plan_id)
    WHERE active_until IS NULL AND plan_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS payment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID REFERENCES payments(id) ON DELETE CASCADE,
    event_type VARCHAR NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_payments_user_id ON payments (user_id);

CREATE INDEX IF NOT EXISTS ix_subscriptions_user_id ON subscriptions (user_id);

CREATE INDEX IF NOT EXISTS ix_payment_events_unprocessed
    ON payment_events (payment_id)
    WHERE processed IS FALSE;

CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    maintenance_mode BOOLEAN NOT NULL DEFAULT false
);

INSERT INTO system_settings (id, maintenance_mode) VALUES (1, false)
ON CONFLICT (id) DO NOTHING;
