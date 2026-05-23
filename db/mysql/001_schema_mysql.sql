-- =============================================================================
-- 001_schema_mysql.sql
-- Doel   : MySQL/MariaDB-variant van het VGBC POC-schema.
--          Geporteerd vanaf db/ddl/001_schema.sql (PostgreSQL).
-- Gebruik: Plak in phpMyAdmin > SQL-tab, of via mysql CLI:
--          mysql -u arjenvangent -p xrfxdlxg_arjenvangent < 001_schema_mysql.sql
-- Vereist: MySQL 8.0.16+ of MariaDB 10.2+ (i.v.m. CHECK constraints).
--          Op oudere versies worden CHECK-clausules stilzwijgend genegeerd —
--          dat is niet fataal, maar minder strikt dan de Postgres-versie.
-- =============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------------
-- Klanten
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS klanten (
    klant_id            INT          NOT NULL AUTO_INCREMENT,
    naam                VARCHAR(200) NOT NULL,
    is_bedrijf          TINYINT(1)   NOT NULL DEFAULT 1,
    straat              VARCHAR(200),
    postcode            VARCHAR(10),
    plaats              VARCHAR(100),
    email               VARCHAR(150),
    telefoon            VARCHAR(30),
    btw_nummer          VARCHAR(20),
    betaaltermijn_dagen INT          NOT NULL DEFAULT 30,
    is_dubieus          TINYINT(1)   NOT NULL DEFAULT 0,
    PRIMARY KEY (klant_id),
    KEY idx_klanten_naam (naam),
    CONSTRAINT ck_klanten_betaaltermijn CHECK (betaaltermijn_dagen > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Leveranciers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS leveranciers (
    leverancier_id INT          NOT NULL AUTO_INCREMENT,
    naam           VARCHAR(200) NOT NULL,
    straat         VARCHAR(200),
    postcode       VARCHAR(10),
    plaats         VARCHAR(100),
    email          VARCHAR(150),
    telefoon       VARCHAR(30),
    iban           VARCHAR(34),
    btw_nummer     VARCHAR(20),
    PRIMARY KEY (leverancier_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Medewerkers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medewerkers (
    medewerker_id   INT          NOT NULL AUTO_INCREMENT,
    naam            VARCHAR(150) NOT NULL,
    rol             VARCHAR(80),
    email           VARCHAR(150),
    uurtarief       DECIMAL(8, 2),
    in_dienst_datum DATE,
    PRIMARY KEY (medewerker_id),
    CONSTRAINT ck_medewerkers_uurtarief CHECK (uurtarief IS NULL OR uurtarief >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Producten en diensten
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS producten_diensten (
    product_id   INT            NOT NULL AUTO_INCREMENT,
    omschrijving VARCHAR(200)   NOT NULL,
    eenheid      VARCHAR(20)    NOT NULL,
    verkoopprijs DECIMAL(10, 2) NOT NULL,
    btw_tarief   DECIMAL(5, 4)  NOT NULL,
    actief       TINYINT(1)     NOT NULL DEFAULT 1,
    PRIMARY KEY (product_id),
    CONSTRAINT ck_prod_verkoopprijs CHECK (verkoopprijs >= 0),
    CONSTRAINT ck_prod_btw_tarief   CHECK (btw_tarief IN (0.0000, 0.0900, 0.2100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Projecten
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projecten (
    project_id        INT            NOT NULL AUTO_INCREMENT,
    naam              VARCHAR(200)   NOT NULL,
    klant_id          INT            NOT NULL,
    status            VARCHAR(20)    NOT NULL,
    startdatum        DATE,
    einddatum         DATE,
    geoffreerd_bedrag DECIMAL(12, 2),
    omschrijving      TEXT,
    PRIMARY KEY (project_id),
    KEY idx_projecten_klant  (klant_id),
    KEY idx_projecten_status (status),
    CONSTRAINT fk_projecten_klant
        FOREIGN KEY (klant_id) REFERENCES klanten (klant_id),
    CONSTRAINT ck_project_status
        CHECK (status IN ('Offerte', 'Lopend', 'Afgerond', 'Geannuleerd')),
    CONSTRAINT ck_project_geoffreerd
        CHECK (geoffreerd_bedrag IS NULL OR geoffreerd_bedrag >= 0),
    CONSTRAINT ck_project_datums
        CHECK (einddatum IS NULL OR startdatum IS NULL OR einddatum >= startdatum)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Urenregistratie
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS urenregistratie (
    uur_id        INT           NOT NULL AUTO_INCREMENT,
    project_id    INT           NOT NULL,
    medewerker_id INT           NOT NULL,
    datum         DATE          NOT NULL,
    uren          DECIMAL(5, 1) NOT NULL,
    omschrijving  TEXT,
    PRIMARY KEY (uur_id),
    KEY idx_uren_project    (project_id),
    KEY idx_uren_medewerker (medewerker_id),
    KEY idx_uren_datum      (datum),
    CONSTRAINT fk_uren_project
        FOREIGN KEY (project_id) REFERENCES projecten (project_id),
    CONSTRAINT fk_uren_medewerker
        FOREIGN KEY (medewerker_id) REFERENCES medewerkers (medewerker_id),
    CONSTRAINT ck_uren_bereik CHECK (uren > 0 AND uren <= 24)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Facturen
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS facturen (
    factuur_id       INT            NOT NULL AUTO_INCREMENT,
    factuurnummer    VARCHAR(30)    NOT NULL,
    klant_id         INT            NOT NULL,
    project_id       INT            NULL,
    datum            DATE           NOT NULL,
    vervaldatum      DATE           NOT NULL,
    bedrag_excl_btw  DECIMAL(12, 2) NOT NULL,
    bedrag_btw       DECIMAL(12, 2) NOT NULL DEFAULT 0,
    bedrag_incl_btw  DECIMAL(12, 2) NOT NULL,
    status           VARCHAR(20)    NOT NULL,
    is_creditfactuur TINYINT(1)     NOT NULL DEFAULT 0,
    PRIMARY KEY (factuur_id),
    UNIQUE KEY uq_facturen_factuurnummer (factuurnummer),
    KEY idx_facturen_klant       (klant_id),
    KEY idx_facturen_status      (status),
    KEY idx_facturen_datum       (datum),
    KEY idx_facturen_vervaldatum (vervaldatum),
    CONSTRAINT fk_facturen_klant
        FOREIGN KEY (klant_id) REFERENCES klanten (klant_id),
    CONSTRAINT fk_facturen_project
        FOREIGN KEY (project_id) REFERENCES projecten (project_id),
    CONSTRAINT ck_facturen_status
        CHECK (status IN ('Betaald', 'Openstaand', 'Achterstallig', 'Gecrediteerd')),
    CONSTRAINT ck_facturen_vervaldatum CHECK (vervaldatum >= datum)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Factuurregels
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS factuurregels (
    regel_id        INT            NOT NULL AUTO_INCREMENT,
    factuur_id      INT            NOT NULL,
    product_id      INT            NOT NULL,
    omschrijving    VARCHAR(200),
    aantal          DECIMAL(10, 2) NOT NULL,
    eenheidsprijs   DECIMAL(10, 2) NOT NULL,
    btw_tarief      DECIMAL(5, 4)  NOT NULL,
    bedrag_excl_btw DECIMAL(12, 2) NOT NULL,
    bedrag_btw      DECIMAL(12, 2) NOT NULL,
    PRIMARY KEY (regel_id),
    KEY idx_regels_factuur (factuur_id),
    KEY idx_regels_product (product_id),
    CONSTRAINT fk_regels_factuur
        FOREIGN KEY (factuur_id) REFERENCES facturen (factuur_id),
    CONSTRAINT fk_regels_product
        FOREIGN KEY (product_id) REFERENCES producten_diensten (product_id),
    CONSTRAINT ck_regels_aantal CHECK (aantal <> 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Betalingen
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS betalingen (
    betaling_id INT            NOT NULL AUTO_INCREMENT,
    factuur_id  INT            NOT NULL,
    datum       DATE           NOT NULL,
    bedrag      DECIMAL(12, 2) NOT NULL,
    methode     VARCHAR(40),
    PRIMARY KEY (betaling_id),
    KEY idx_betalingen_factuur (factuur_id),
    KEY idx_betalingen_datum   (datum),
    CONSTRAINT fk_betalingen_factuur
        FOREIGN KEY (factuur_id) REFERENCES facturen (factuur_id),
    CONSTRAINT ck_betalingen_bedrag CHECK (bedrag > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Inkoopfacturen
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inkoopfacturen (
    inkoop_id       INT            NOT NULL AUTO_INCREMENT,
    inkoopnummer    VARCHAR(30)    NOT NULL,
    leverancier_id  INT            NOT NULL,
    datum           DATE           NOT NULL,
    vervaldatum     DATE           NOT NULL,
    omschrijving    TEXT,
    bedrag_excl_btw DECIMAL(12, 2) NOT NULL,
    btw_tarief      DECIMAL(5, 4)  NOT NULL,
    bedrag_btw      DECIMAL(12, 2) NOT NULL,
    bedrag_incl_btw DECIMAL(12, 2) NOT NULL,
    status          VARCHAR(20)    NOT NULL,
    PRIMARY KEY (inkoop_id),
    UNIQUE KEY uq_inkoop_inkoopnummer (inkoopnummer),
    KEY idx_inkoop_leverancier (leverancier_id),
    KEY idx_inkoop_status      (status),
    KEY idx_inkoop_vervaldatum (vervaldatum),
    CONSTRAINT fk_inkoop_leverancier
        FOREIGN KEY (leverancier_id) REFERENCES leveranciers (leverancier_id),
    CONSTRAINT ck_inkoop_status
        CHECK (status IN ('Betaald', 'Openstaand', 'Achterstallig')),
    CONSTRAINT ck_inkoop_vervaldatum CHECK (vervaldatum >= datum)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
