-- SkyBook account settings
-- Adds persistent notification preference for authenticated users.

ALTER TABLE "Users"
ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE;
