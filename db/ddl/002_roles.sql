-- =============================================================================
-- 002_roles.sql
-- Doel   : Aanmaken van de read-only databasegebruiker 'vgbc_agent' die de
--          AI-chatbot gebruikt. Deze rol heeft uitsluitend SELECT-rechten.
-- Gebruik: psql -U vgbc_user -d vgbc_poc -f db/ddl/002_roles.sql
-- =============================================================================

-- Maak de read-only rol aan als die nog niet bestaat
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vgbc_agent') THEN
        CREATE ROLE vgbc_agent LOGIN PASSWORD 'agent_readonly_pw';
    END IF;
END
$$;

-- Verbinding naar de database toestaan
GRANT CONNECT ON DATABASE vgbc_poc TO vgbc_agent;

-- SELECT-rechten op alle bestaande tabellen
GRANT USAGE  ON SCHEMA public TO vgbc_agent;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO vgbc_agent;

-- SELECT-rechten ook op toekomstige tabellen (default privileges)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO vgbc_agent;
