-- =============================================================================
-- 000_init_db.sql
-- Doel   : Eenmalige initialisatie — aanmaken van database en schrijfgebruiker.
-- Gebruik: Verbind als superuser (postgres) en voer dit script uit:
--          psql -U postgres -f db/ddl/000_init_db.sql
-- =============================================================================

-- Schrijfgebruiker aanmaken (als nog niet bestaat)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vgbc_user') THEN
        CREATE ROLE vgbc_user LOGIN PASSWORD 'kies_een_sterk_wachtwoord';
    END IF;
END
$$;

-- Database aanmaken (als nog niet bestaat)
-- Gebruik template1 zodat de systeemlokaal van Windows behouden blijft.
SELECT 'CREATE DATABASE vgbc_poc OWNER vgbc_user ENCODING ''UTF8'' TEMPLATE template1'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'vgbc_poc')\gexec

GRANT ALL PRIVILEGES ON DATABASE vgbc_poc TO vgbc_user;
