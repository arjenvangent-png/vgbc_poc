-- =============================================================================
-- 001_schema.sql
-- Doel   : Aanmaken van alle tabellen, PKs, FKs, indexen en check-constraints
--          voor de VGBC POC. Branche-onafhankelijk universeel MKB-datamodel.
-- Gebruik: psql -U vgbc_user -d vgbc_poc -f db/ddl/001_schema.sql
-- =============================================================================

SET client_encoding = 'UTF8';

-- ---------------------------------------------------------------------------
-- Klanten
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS klanten (
    klant_id           SERIAL PRIMARY KEY,
    naam               VARCHAR(200) NOT NULL,
    is_bedrijf         BOOLEAN      NOT NULL DEFAULT TRUE,
    straat             VARCHAR(200),
    postcode           VARCHAR(10),
    plaats             VARCHAR(100),
    email              VARCHAR(150),
    telefoon           VARCHAR(30),
    btw_nummer         VARCHAR(20),
    betaaltermijn_dagen INTEGER      NOT NULL DEFAULT 30 CHECK (betaaltermijn_dagen > 0),
    is_dubieus         BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_klanten_naam ON klanten (naam);

-- ---------------------------------------------------------------------------
-- Leveranciers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS leveranciers (
    leverancier_id SERIAL PRIMARY KEY,
    naam           VARCHAR(200) NOT NULL,
    straat         VARCHAR(200),
    postcode       VARCHAR(10),
    plaats         VARCHAR(100),
    email          VARCHAR(150),
    telefoon       VARCHAR(30),
    iban           VARCHAR(34),
    btw_nummer     VARCHAR(20)
);

-- ---------------------------------------------------------------------------
-- Medewerkers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medewerkers (
    medewerker_id   SERIAL PRIMARY KEY,
    naam            VARCHAR(150) NOT NULL,
    rol             VARCHAR(80),
    email           VARCHAR(150),
    uurtarief       NUMERIC(8, 2) CHECK (uurtarief >= 0),
    in_dienst_datum DATE
);

-- ---------------------------------------------------------------------------
-- Producten en diensten
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS producten_diensten (
    product_id    SERIAL PRIMARY KEY,
    omschrijving  VARCHAR(200) NOT NULL,
    eenheid       VARCHAR(20)  NOT NULL,
    verkoopprijs  NUMERIC(10, 2) NOT NULL CHECK (verkoopprijs >= 0),
    btw_tarief    NUMERIC(5, 4) NOT NULL CHECK (btw_tarief IN (0.00, 0.09, 0.21)),
    actief        BOOLEAN NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------------
-- Projecten
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projecten (
    project_id         SERIAL PRIMARY KEY,
    naam               VARCHAR(200) NOT NULL,
    klant_id           INTEGER NOT NULL REFERENCES klanten (klant_id),
    status             VARCHAR(20) NOT NULL
                           CHECK (status IN ('Offerte', 'Lopend', 'Afgerond', 'Geannuleerd')),
    startdatum         DATE,
    einddatum          DATE,
    geoffreerd_bedrag  NUMERIC(12, 2) CHECK (geoffreerd_bedrag >= 0),
    omschrijving       TEXT,
    CONSTRAINT ck_project_datums CHECK (einddatum IS NULL OR einddatum >= startdatum)
);

CREATE INDEX IF NOT EXISTS idx_projecten_klant    ON projecten (klant_id);
CREATE INDEX IF NOT EXISTS idx_projecten_status   ON projecten (status);

-- ---------------------------------------------------------------------------
-- Urenregistratie
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS urenregistratie (
    uur_id        SERIAL PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projecten    (project_id),
    medewerker_id INTEGER NOT NULL REFERENCES medewerkers  (medewerker_id),
    datum         DATE    NOT NULL,
    uren          NUMERIC(5, 1) NOT NULL CHECK (uren > 0 AND uren <= 24),
    omschrijving  TEXT
);

CREATE INDEX IF NOT EXISTS idx_uren_project    ON urenregistratie (project_id);
CREATE INDEX IF NOT EXISTS idx_uren_medewerker ON urenregistratie (medewerker_id);
CREATE INDEX IF NOT EXISTS idx_uren_datum      ON urenregistratie (datum);

-- ---------------------------------------------------------------------------
-- Facturen
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS facturen (
    factuur_id       SERIAL PRIMARY KEY,
    factuurnummer    VARCHAR(30)  NOT NULL UNIQUE,
    klant_id         INTEGER      NOT NULL REFERENCES klanten  (klant_id),
    project_id       INTEGER               REFERENCES projecten (project_id),
    datum            DATE         NOT NULL,
    vervaldatum      DATE         NOT NULL,
    bedrag_excl_btw  NUMERIC(12, 2) NOT NULL,
    bedrag_btw       NUMERIC(12, 2) NOT NULL DEFAULT 0,
    bedrag_incl_btw  NUMERIC(12, 2) NOT NULL,
    status           VARCHAR(20)  NOT NULL
                         CHECK (status IN ('Betaald', 'Openstaand', 'Achterstallig', 'Gecrediteerd')),
    is_creditfactuur BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT ck_factuur_vervaldatum CHECK (vervaldatum >= datum)
);

CREATE INDEX IF NOT EXISTS idx_facturen_klant      ON facturen (klant_id);
CREATE INDEX IF NOT EXISTS idx_facturen_status     ON facturen (status);
CREATE INDEX IF NOT EXISTS idx_facturen_datum      ON facturen (datum);
CREATE INDEX IF NOT EXISTS idx_facturen_vervaldatum ON facturen (vervaldatum);

-- ---------------------------------------------------------------------------
-- Factuurregels
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS factuurregels (
    regel_id        SERIAL PRIMARY KEY,
    factuur_id      INTEGER        NOT NULL REFERENCES facturen        (factuur_id),
    product_id      INTEGER        NOT NULL REFERENCES producten_diensten (product_id),
    omschrijving    VARCHAR(200),
    aantal          NUMERIC(10, 2) NOT NULL CHECK (aantal <> 0),
    eenheidsprijs   NUMERIC(10, 2) NOT NULL,
    btw_tarief      NUMERIC(5, 4)  NOT NULL,
    bedrag_excl_btw NUMERIC(12, 2) NOT NULL,
    bedrag_btw      NUMERIC(12, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_regels_factuur  ON factuurregels (factuur_id);
CREATE INDEX IF NOT EXISTS idx_regels_product  ON factuurregels (product_id);

-- ---------------------------------------------------------------------------
-- Betalingen
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS betalingen (
    betaling_id SERIAL PRIMARY KEY,
    factuur_id  INTEGER        NOT NULL REFERENCES facturen (factuur_id),
    datum       DATE           NOT NULL,
    bedrag      NUMERIC(12, 2) NOT NULL CHECK (bedrag > 0),
    methode     VARCHAR(40)
);

CREATE INDEX IF NOT EXISTS idx_betalingen_factuur ON betalingen (factuur_id);
CREATE INDEX IF NOT EXISTS idx_betalingen_datum   ON betalingen (datum);

-- ---------------------------------------------------------------------------
-- Inkoopfacturen
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inkoopfacturen (
    inkoop_id       SERIAL PRIMARY KEY,
    inkoopnummer    VARCHAR(30)    NOT NULL UNIQUE,
    leverancier_id  INTEGER        NOT NULL REFERENCES leveranciers (leverancier_id),
    datum           DATE           NOT NULL,
    vervaldatum     DATE           NOT NULL,
    omschrijving    TEXT,
    bedrag_excl_btw NUMERIC(12, 2) NOT NULL,
    btw_tarief      NUMERIC(5, 4)  NOT NULL,
    bedrag_btw      NUMERIC(12, 2) NOT NULL,
    bedrag_incl_btw NUMERIC(12, 2) NOT NULL,
    status          VARCHAR(20)    NOT NULL
                        CHECK (status IN ('Betaald', 'Openstaand', 'Achterstallig')),
    CONSTRAINT ck_inkoop_vervaldatum CHECK (vervaldatum >= datum)
);

CREATE INDEX IF NOT EXISTS idx_inkoop_leverancier  ON inkoopfacturen (leverancier_id);
CREATE INDEX IF NOT EXISTS idx_inkoop_status       ON inkoopfacturen (status);
CREATE INDEX IF NOT EXISTS idx_inkoop_vervaldatum  ON inkoopfacturen (vervaldatum);
