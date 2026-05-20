-- =============================================================================
-- views.sql
-- Doel   : Rapportage-views die de AI-agent en dashboards gemakkelijk kunnen
--          bevragen. Alle views zijn read-only en bevatten geen gevoelige data.
-- Views  : v_omzet_per_maand, v_openstaande_debiteuren, v_marge_per_project,
--          v_top_klanten, v_cashflow_per_week, v_btw_per_kwartaal,
--          v_openstaande_inkoopfacturen
-- Gebruik: psql -U vgbc_user -d vgbc_poc -f db/views/views.sql
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Omzet per maand (gefactureerde omzet exclusief BTW, alleen verkoopfacturen)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_omzet_per_maand AS
SELECT
    DATE_TRUNC('month', datum)::DATE AS maand,
    TO_CHAR(datum, 'YYYY-MM')        AS jaar_maand,
    COUNT(*)                          AS aantal_facturen,
    SUM(bedrag_excl_btw)              AS omzet_excl_btw,
    SUM(bedrag_btw)                   AS btw_bedrag,
    SUM(bedrag_incl_btw)              AS omzet_incl_btw
FROM facturen
WHERE is_creditfactuur = FALSE
GROUP BY DATE_TRUNC('month', datum), TO_CHAR(datum, 'YYYY-MM')
ORDER BY maand;

-- ---------------------------------------------------------------------------
-- Openstaande debiteuren (facturen die nog betaald moeten worden)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_openstaande_debiteuren AS
SELECT
    f.factuur_id,
    f.factuurnummer,
    k.naam                                        AS klant,
    k.email                                       AS klant_email,
    k.is_dubieus,
    f.datum                                       AS factuurdatum,
    f.vervaldatum,
    CURRENT_DATE - f.vervaldatum                  AS dagen_achterstallig,
    CASE
        WHEN CURRENT_DATE <= f.vervaldatum THEN 'Nog niet vervallen'
        WHEN CURRENT_DATE - f.vervaldatum <= 30  THEN '0-30 dagen'
        WHEN CURRENT_DATE - f.vervaldatum <= 60  THEN '31-60 dagen'
        WHEN CURRENT_DATE - f.vervaldatum <= 90  THEN '61-90 dagen'
        ELSE '> 90 dagen'
    END                                           AS vervalcategorie,
    f.bedrag_incl_btw                             AS openstaand_bedrag
FROM facturen f
JOIN klanten k ON k.klant_id = f.klant_id
WHERE f.status IN ('Openstaand', 'Achterstallig')
ORDER BY dagen_achterstallig DESC NULLS LAST, f.bedrag_incl_btw DESC;

-- ---------------------------------------------------------------------------
-- Marge per project (geoffreerd vs. gefactureerd vs. kosten op basis van uren)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_marge_per_project AS
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
LEFT JOIN facturen       f ON f.project_id = p.project_id AND f.is_creditfactuur = FALSE
LEFT JOIN urenregistratie u ON u.project_id = p.project_id
LEFT JOIN medewerkers    m ON m.medewerker_id = u.medewerker_id
GROUP BY p.project_id, p.naam, k.naam, p.status, p.startdatum, p.einddatum, p.geoffreerd_bedrag;

-- ---------------------------------------------------------------------------
-- Top klanten op omzet (gecumuleerd, excl. creditfacturen)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_top_klanten AS
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
                  WHERE is_creditfactuur = FALSE), 0) * 100, 2
    )                                                AS aandeel_pct
FROM klanten k
JOIN facturen f ON f.klant_id = k.klant_id
WHERE f.is_creditfactuur = FALSE
GROUP BY k.klant_id, k.naam, k.is_bedrijf, k.is_dubieus
ORDER BY omzet_excl_btw DESC;

-- ---------------------------------------------------------------------------
-- Cashflow per week (ontvangen betalingen minus betaalde inkoopfacturen)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_cashflow_per_week AS
WITH inkomsten AS (
    SELECT
        DATE_TRUNC('week', datum)::DATE AS week_start,
        SUM(bedrag)                      AS ontvangen
    FROM betalingen
    GROUP BY DATE_TRUNC('week', datum)
),
uitgaven AS (
    SELECT
        DATE_TRUNC('week', vervaldatum)::DATE AS week_start,
        SUM(bedrag_incl_btw)                  AS betaald
    FROM inkoopfacturen
    WHERE status = 'Betaald'
    GROUP BY DATE_TRUNC('week', vervaldatum)
)
SELECT
    COALESCE(i.week_start, u.week_start)           AS week_start,
    COALESCE(i.ontvangen, 0)                        AS inkomsten,
    COALESCE(u.betaald, 0)                          AS uitgaven,
    COALESCE(i.ontvangen, 0) - COALESCE(u.betaald, 0) AS netto_cashflow
FROM inkomsten  i
FULL OUTER JOIN uitgaven u ON u.week_start = i.week_start
ORDER BY week_start;

-- ---------------------------------------------------------------------------
-- BTW-aangifte per kwartaal (te betalen = verkoop-BTW minus inkoop-BTW)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_btw_per_kwartaal AS
WITH verkoop AS (
    SELECT
        DATE_PART('year',    datum)::INT AS jaar,
        DATE_PART('quarter', datum)::INT AS kwartaal,
        SUM(bedrag_btw)                  AS verkoop_btw
    FROM facturen
    WHERE is_creditfactuur = FALSE
    GROUP BY 1, 2
),
inkoop AS (
    SELECT
        DATE_PART('year',    datum)::INT AS jaar,
        DATE_PART('quarter', datum)::INT AS kwartaal,
        SUM(bedrag_btw)                  AS inkoop_btw
    FROM inkoopfacturen
    GROUP BY 1, 2
)
SELECT
    COALESCE(v.jaar,     i.jaar)     AS jaar,
    COALESCE(v.kwartaal, i.kwartaal) AS kwartaal,
    COALESCE(v.verkoop_btw, 0)       AS af_te_dragen_btw,
    COALESCE(i.inkoop_btw,  0)       AS terug_te_vorderen_btw,
    COALESCE(v.verkoop_btw, 0) - COALESCE(i.inkoop_btw, 0) AS saldo_btw
FROM verkoop v
FULL OUTER JOIN inkoop i ON i.jaar = v.jaar AND i.kwartaal = v.kwartaal
ORDER BY jaar, kwartaal;

-- ---------------------------------------------------------------------------
-- Openstaande inkoopfacturen (te betalen aan leveranciers)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_openstaande_inkoopfacturen AS
SELECT
    i.inkoop_id,
    i.inkoopnummer,
    l.naam                              AS leverancier,
    l.iban,
    i.datum,
    i.vervaldatum,
    CURRENT_DATE - i.vervaldatum        AS dagen_achterstallig,
    i.bedrag_incl_btw                   AS te_betalen,
    i.status
FROM inkoopfacturen i
JOIN leveranciers l ON l.leverancier_id = i.leverancier_id
WHERE i.status IN ('Openstaand', 'Achterstallig')
ORDER BY i.vervaldatum ASC;
