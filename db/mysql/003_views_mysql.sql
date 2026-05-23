-- =============================================================================
-- 003_views_mysql.sql
-- Doel   : MySQL/MariaDB-variant van de rapportage-views.
--          Geporteerd vanaf db/views/views.sql (PostgreSQL).
-- Gebruik: Voer uit NA 001_schema_mysql.sql en NA de CSV-import.
-- Verschillen t.o.v. Postgres-origineel:
--   - DATE_TRUNC('month', d)  -> DATE_FORMAT(d, '%Y-%m-01')
--   - DATE_TRUNC('week',  d)  -> DATE_SUB(d, INTERVAL WEEKDAY(d) DAY)   (maandag-start)
--   - TO_CHAR(d, 'YYYY-MM')   -> DATE_FORMAT(d, '%Y-%m')
--   - CURRENT_DATE            -> CURDATE()
--   - d1 - d2 (interval)      -> DATEDIFF(d1, d2)
--   - FULL OUTER JOIN         -> UNION-truc met LEFT JOIN
--   - NULLS LAST              -> CASE WHEN ... IS NULL ... ORDER trick
-- =============================================================================

SET NAMES utf8mb4;

-- ---------------------------------------------------------------------------
-- Omzet per maand
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_omzet_per_maand;
CREATE VIEW v_omzet_per_maand AS
SELECT
    DATE_FORMAT(datum, '%Y-%m-01')   AS maand,
    DATE_FORMAT(datum, '%Y-%m')      AS jaar_maand,
    COUNT(*)                          AS aantal_facturen,
    SUM(bedrag_excl_btw)              AS omzet_excl_btw,
    SUM(bedrag_btw)                   AS btw_bedrag,
    SUM(bedrag_incl_btw)              AS omzet_incl_btw
FROM facturen
WHERE is_creditfactuur = 0
GROUP BY DATE_FORMAT(datum, '%Y-%m-01'), DATE_FORMAT(datum, '%Y-%m')
ORDER BY maand;

-- ---------------------------------------------------------------------------
-- Openstaande debiteuren
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_openstaande_debiteuren;
CREATE VIEW v_openstaande_debiteuren AS
SELECT
    f.factuur_id,
    f.factuurnummer,
    k.naam                                AS klant,
    k.email                               AS klant_email,
    k.is_dubieus,
    f.datum                               AS factuurdatum,
    f.vervaldatum,
    DATEDIFF(CURDATE(), f.vervaldatum)    AS dagen_achterstallig,
    CASE
        WHEN CURDATE() <= f.vervaldatum                       THEN 'Nog niet vervallen'
        WHEN DATEDIFF(CURDATE(), f.vervaldatum) <= 30         THEN '0-30 dagen'
        WHEN DATEDIFF(CURDATE(), f.vervaldatum) <= 60         THEN '31-60 dagen'
        WHEN DATEDIFF(CURDATE(), f.vervaldatum) <= 90         THEN '61-90 dagen'
        ELSE '> 90 dagen'
    END                                   AS vervalcategorie,
    f.bedrag_incl_btw                     AS openstaand_bedrag
FROM facturen f
JOIN klanten k ON k.klant_id = f.klant_id
WHERE f.status IN ('Openstaand', 'Achterstallig')
ORDER BY dagen_achterstallig DESC, f.bedrag_incl_btw DESC;

-- ---------------------------------------------------------------------------
-- Marge per project
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_marge_per_project;
CREATE VIEW v_marge_per_project AS
SELECT
    p.project_id,
    p.naam                                              AS project,
    k.naam                                              AS klant,
    p.status,
    p.startdatum,
    p.einddatum,
    p.geoffreerd_bedrag,
    COALESCE(SUM(DISTINCT f.bedrag_excl_btw), 0)        AS gefactureerd_excl_btw,
    COALESCE(SUM(u.uren * m.uurtarief), 0)              AS kosten_uren,
    COALESCE(SUM(DISTINCT f.bedrag_excl_btw), 0)
        - COALESCE(SUM(u.uren * m.uurtarief), 0)        AS bruto_marge,
    CASE
        WHEN COALESCE(SUM(DISTINCT f.bedrag_excl_btw), 0) = 0 THEN NULL
        ELSE ROUND(
            (COALESCE(SUM(DISTINCT f.bedrag_excl_btw), 0)
             - COALESCE(SUM(u.uren * m.uurtarief), 0))
            / COALESCE(SUM(DISTINCT f.bedrag_excl_btw), 0) * 100, 1)
    END                                                 AS marge_pct
FROM projecten p
JOIN klanten k ON k.klant_id = p.klant_id
LEFT JOIN facturen        f ON f.project_id = p.project_id AND f.is_creditfactuur = 0
LEFT JOIN urenregistratie u ON u.project_id = p.project_id
LEFT JOIN medewerkers     m ON m.medewerker_id = u.medewerker_id
GROUP BY p.project_id, p.naam, k.naam, p.status, p.startdatum, p.einddatum, p.geoffreerd_bedrag;

-- ---------------------------------------------------------------------------
-- Top klanten op omzet
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_top_klanten;
CREATE VIEW v_top_klanten AS
SELECT
    k.klant_id,
    k.naam,
    k.is_bedrijf,
    k.is_dubieus,
    COUNT(f.factuur_id)                              AS aantal_facturen,
    SUM(f.bedrag_excl_btw)                           AS omzet_excl_btw,
    SUM(f.bedrag_incl_btw)                           AS omzet_incl_btw,
    ROUND(
        SUM(f.bedrag_excl_btw)
        / NULLIF((SELECT SUM(bedrag_excl_btw) FROM facturen
                  WHERE is_creditfactuur = 0), 0) * 100, 2
    )                                                AS aandeel_pct
FROM klanten k
JOIN facturen f ON f.klant_id = k.klant_id
WHERE f.is_creditfactuur = 0
GROUP BY k.klant_id, k.naam, k.is_bedrijf, k.is_dubieus
ORDER BY omzet_excl_btw DESC;

-- ---------------------------------------------------------------------------
-- Cashflow per week
-- MySQL kent geen FULL OUTER JOIN, dus we doen UNION van twee LEFT JOINs.
-- Week-start = maandag (WEEKDAY: ma=0..zo=6).
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_cashflow_per_week;
CREATE VIEW v_cashflow_per_week AS
SELECT
    week_start,
    SUM(inkomsten) AS inkomsten,
    SUM(uitgaven)  AS uitgaven,
    SUM(inkomsten) - SUM(uitgaven) AS netto_cashflow
FROM (
    SELECT
        DATE_SUB(datum, INTERVAL WEEKDAY(datum) DAY) AS week_start,
        SUM(bedrag)                                  AS inkomsten,
        0                                            AS uitgaven
    FROM betalingen
    GROUP BY DATE_SUB(datum, INTERVAL WEEKDAY(datum) DAY)

    UNION ALL

    SELECT
        DATE_SUB(vervaldatum, INTERVAL WEEKDAY(vervaldatum) DAY) AS week_start,
        0                                                          AS inkomsten,
        SUM(bedrag_incl_btw)                                       AS uitgaven
    FROM inkoopfacturen
    WHERE status = 'Betaald'
    GROUP BY DATE_SUB(vervaldatum, INTERVAL WEEKDAY(vervaldatum) DAY)
) cf
GROUP BY week_start
ORDER BY week_start;

-- ---------------------------------------------------------------------------
-- BTW per kwartaal
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_btw_per_kwartaal;
CREATE VIEW v_btw_per_kwartaal AS
SELECT
    jaar,
    kwartaal,
    SUM(verkoop_btw) AS af_te_dragen_btw,
    SUM(inkoop_btw)  AS terug_te_vorderen_btw,
    SUM(verkoop_btw) - SUM(inkoop_btw) AS saldo_btw
FROM (
    SELECT
        YEAR(datum)    AS jaar,
        QUARTER(datum) AS kwartaal,
        SUM(bedrag_btw) AS verkoop_btw,
        0               AS inkoop_btw
    FROM facturen
    WHERE is_creditfactuur = 0
    GROUP BY YEAR(datum), QUARTER(datum)

    UNION ALL

    SELECT
        YEAR(datum)    AS jaar,
        QUARTER(datum) AS kwartaal,
        0               AS verkoop_btw,
        SUM(bedrag_btw) AS inkoop_btw
    FROM inkoopfacturen
    GROUP BY YEAR(datum), QUARTER(datum)
) btw
GROUP BY jaar, kwartaal
ORDER BY jaar, kwartaal;

-- ---------------------------------------------------------------------------
-- Openstaande inkoopfacturen
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_openstaande_inkoopfacturen;
CREATE VIEW v_openstaande_inkoopfacturen AS
SELECT
    i.inkoop_id,
    i.inkoopnummer,
    l.naam                              AS leverancier,
    l.iban,
    i.datum,
    i.vervaldatum,
    DATEDIFF(CURDATE(), i.vervaldatum)  AS dagen_achterstallig,
    i.bedrag_incl_btw                   AS te_betalen,
    i.status
FROM inkoopfacturen i
JOIN leveranciers l ON l.leverancier_id = i.leverancier_id
WHERE i.status IN ('Openstaand', 'Achterstallig')
ORDER BY i.vervaldatum ASC;
