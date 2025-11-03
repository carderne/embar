-- Generated Migration SQL
-- =======================

-- Migration 1/2
-- Table: users
-- Type: NEW
-- Compatibility: BACKWARD-COMPATIBLE
-- Explanation: This migration creates a new table "users" if it doesn't already exist, which is a safe operation. It adds columns with sensible defaults and allows nullable fields. The CREATE TABLE IF NOT EXISTS clause ensures no existing data is disrupted, and the migration only introduces a new table structure without modifying any existing database objects.

CREATE TABLE IF NOT EXISTS "users" (
    "id" INTEGER PRIMARY KEY,
    "user_email" TEXT NOT NULL,
    "username" TEXT,
    "created_at" TEXT DEFAULT 'now()'
);


-- Migration 2/2
-- Table: message
-- Type: NEW
-- Compatibility: BACKWARD-COMPATIBLE
-- Explanation: This migration creates a new table "message" with default values, primary and foreign key constraints, which will not break existing database code. The DEFAULT 'no message' for "content" ensures existing insert operations will work, and the table is created conditionally (IF NOT EXISTS), preventing accidental overwrites or disruptions.

CREATE TABLE IF NOT EXISTS "message" (
    "id" INTEGER PRIMARY KEY,
    "user_id" INTEGER,
    "content" TEXT DEFAULT 'no message',
    FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE
);

