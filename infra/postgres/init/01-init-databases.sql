-- Create the MLflow backend database alongside the application database.
-- The application DB (sentinellerx) is created by the postgres image via env vars.
SELECT 'CREATE DATABASE mlflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mlflow')\gexec

-- Enable required extensions on the application database.
\connect sentinellerx
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
