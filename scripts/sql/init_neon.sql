-- =============================================================================
-- BREW & BEAN (cafe-digital-platform)
-- Script khởi tạo PostgreSQL 17 Extensions & Phân quyền Least-Privilege
-- Dùng chung cho:
--   1. PostgreSQL 17 Local Native (Giai đoạn P0-P6)
--   2. Neon PostgreSQL 17 Production (Giai đoạn P7)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Tạo role landing_app_user (Least-Privilege cho Backend khi chạy Production)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'landing_app_user') THEN
        CREATE ROLE landing_app_user WITH LOGIN PASSWORD 'landing_readonly_pass';
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO landing_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO landing_app_user;
