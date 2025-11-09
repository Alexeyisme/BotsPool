-- BotsPool Gateway Database Initialization
-- This script sets up the initial database schema

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create database if not exists (handled by PostgreSQL)
-- The database is created by the POSTGRES_DB environment variable

-- Create initial tables (these will be managed by Alembic migrations)
-- This is just a placeholder for any initial setup

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE botspool_prod TO botspool;
