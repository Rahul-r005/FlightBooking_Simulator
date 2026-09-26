-- PostgreSQL migration for authenticated SkyBook accounts and booking ownership.
-- Existing bookings remain nullable in user_id because they predate account ownership.

CREATE TABLE IF NOT EXISTS "Users" (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    suspended BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "UserSessions" (
    session_id SERIAL PRIMARY KEY,
    token_digest VARCHAR(64) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES "Users"(user_id),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "Notifications" (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "Users"(user_id),
    booking_id INTEGER REFERENCES "Bookings"(booking_id),
    message VARCHAR(500) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read BOOLEAN NOT NULL DEFAULT FALSE
);

ALTER TABLE "Bookings"
    ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES "Users"(user_id);

CREATE INDEX IF NOT EXISTS idx_users_role ON "Users"(role);
CREATE INDEX IF NOT EXISTS idx_users_suspended ON "Users"(suspended);
CREATE INDEX IF NOT EXISTS idx_sessions_token_digest ON "UserSessions"(token_digest);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON "UserSessions"(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON "UserSessions"(expires_at);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON "Notifications"(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_booking_id ON "Notifications"(booking_id);
CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON "Bookings"(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON "Bookings"(status);
CREATE INDEX IF NOT EXISTS idx_bookings_date ON "Bookings"(booking_date);
