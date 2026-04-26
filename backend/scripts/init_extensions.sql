-- Loaded by Postgres on first container boot via the docker-compose volume
-- mount at /docker-entrypoint-initdb.d/10_extensions.sql. Phase 4 (search)
-- and Phase 5 (bookings) both depend on these being present from day one.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS btree_gist;
