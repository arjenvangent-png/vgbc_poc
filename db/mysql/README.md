# VGBC POC — MySQL-variant + phpMyAdmin import

Deze map bevat de MySQL/MariaDB-port van het VGBC POC-schema, zodat de data in
de MySQL-database bij de hosting (phpMyAdmin) gelaten kan worden. De
PostgreSQL-bestanden in `db/ddl/` en `db/views/` blijven het lokale origineel.

## Inhoud

```
db/mysql/
├── 001_schema_mysql.sql        Tabellen, PKs, FKs, indexen, CHECK-constraints
├── 003_views_mysql.sql         7 rapportage-views (Postgres-functies vertaald)
├── csv/                        Import-klare CSV's (booleans 1/0 i.p.v. True/False)
│   ├── klanten.csv
│   ├── leveranciers.csv
│   ├── medewerkers.csv
│   ├── producten_diensten.csv
│   ├── projecten.csv
│   ├── urenregistratie.csv
│   ├── facturen.csv
│   ├── factuurregels.csv
│   ├── betalingen.csv
│   └── inkoopfacturen.csv
└── README.md                   Dit bestand
```

## Vereisten

- Toegang tot phpMyAdmin op je hosting.
- Database `xrfxdlxg_arjenvangent` bestaat al (door hosting aangemaakt).
- MySQL 8.0.16+ of MariaDB 10.2+ aanbevolen — i.v.m. `CHECK`-constraints.
  Op oudere versies worden CHECKs stilzwijgend genegeerd; dat breekt niets,
  maar je verliest één laag dataset-validatie.

## Stap-voor-stap import (10-15 minuten)

### 1. Schema aanmaken

1. Open phpMyAdmin, klik links op database `xrfxdlxg_arjenvangent`.
2. Klik bovenaan op het tabblad **SQL**.
3. Open `001_schema_mysql.sql` in een tekstbewerker, kopieer alle inhoud.
4. Plak in het SQL-veld van phpMyAdmin, klik **Start** (rechtsonder).
5. Verwacht: "Uw SQL-query is succesvol uitgevoerd". Links zou je nu 10 tabellen
   moeten zien staan.

> Treedt er een foutmelding op over `CHECK` of `CONSTRAINT`? Dan draait de
> hosting op een oudere MySQL/MariaDB-versie. Oplossing: verwijder uit
> `001_schema_mysql.sql` alle regels die beginnen met `CONSTRAINT ck_…` en
> de bijbehorende `CHECK (...)`-clausule, en draai opnieuw. Schema blijft
> functioneel; alleen de extra validatie valt weg.

### 2. CSV's importeren — in deze volgorde

Belangrijk: parent-tabellen eerst, anders falen de foreign keys. Doe het in
**deze volgorde**:

1. `klanten.csv`            (80 rijen)
2. `leveranciers.csv`       (20 rijen)
3. `medewerkers.csv`        (8 rijen)
4. `producten_diensten.csv` (30 rijen)
5. `projecten.csv`          (150 rijen)
6. `urenregistratie.csv`    (5000 rijen)
7. `facturen.csv`           (2500 rijen)
8. `factuurregels.csv`      (8717 rijen)
9. `betalingen.csv`         (2036 rijen)
10. `inkoopfacturen.csv`    (1200 rijen)

Per CSV:

1. Klik op de tabelnaam links (bv. `klanten`).
2. Klik bovenaan op tabblad **Importeren**.
3. **Bestand:** kies het bijbehorende CSV uit `db/mysql/csv/`.
4. **Karaktercodering bestand:** `utf-8`.
5. **Indeling:** `CSV`.
6. Onder **Indeling-specifieke opties** instellen:
   - Velden gescheiden door: `,` (komma)
   - Velden omgeven door: `"` (dubbele aanhalingstekens)
   - Velden ontsnapt door: `"` (dubbele aanhalingstekens — let op, niet `\`)
   - Regels eindigen op: `auto`
   - **Het eerste regelnummer dat wordt overgeslagen** ofwel
     **De eerste regel van het bestand bevat de tabel kolommen**: vink **AAN**.
7. Klik **Start**.
8. Verwacht: "Import is succesvol uitgevoerd, X queries uitgevoerd."

> **Tip:** als phpMyAdmin per ongeluk de auto-increment niet juist meeneemt,
> kan dat — de `klant_id`/`factuur_id`/etc. zitten in de CSV's, dus die
> waarden worden expliciet ingevoerd. AUTO_INCREMENT wordt automatisch
> bijgewerkt op `MAX(id) + 1` na de import.

### 3. Views toevoegen

1. Open `003_views_mysql.sql`, kopieer alle inhoud.
2. Plak in phpMyAdmin > SQL-tab, klik **Start**.
3. Links onder de tabellen verschijnt een sectie "Views" met 7 entries.

### 4. Verificatie

Plak deze query in phpMyAdmin > SQL-tab om alle rij-aantallen te bevestigen:

```sql
SELECT 'klanten' AS tabel, COUNT(*) FROM klanten
UNION ALL SELECT 'leveranciers',       COUNT(*) FROM leveranciers
UNION ALL SELECT 'medewerkers',        COUNT(*) FROM medewerkers
UNION ALL SELECT 'producten_diensten', COUNT(*) FROM producten_diensten
UNION ALL SELECT 'projecten',          COUNT(*) FROM projecten
UNION ALL SELECT 'urenregistratie',    COUNT(*) FROM urenregistratie
UNION ALL SELECT 'facturen',           COUNT(*) FROM facturen
UNION ALL SELECT 'factuurregels',      COUNT(*) FROM factuurregels
UNION ALL SELECT 'betalingen',         COUNT(*) FROM betalingen
UNION ALL SELECT 'inkoopfacturen',     COUNT(*) FROM inkoopfacturen;
```

Verwachte uitkomst:

| tabel | aantal |
|---|---|
| klanten | 80 |
| leveranciers | 20 |
| medewerkers | 8 |
| producten_diensten | 30 |
| projecten | 150 |
| urenregistratie | 5000 |
| facturen | 2500 |
| factuurregels | 8717 |
| betalingen | 2036 |
| inkoopfacturen | 1200 |

En test één van de views:

```sql
SELECT * FROM v_omzet_per_maand ORDER BY maand DESC LIMIT 12;
SELECT * FROM v_top_klanten LIMIT 10;
```

## Veiligheidsnotitie

De hosting heeft één database-gebruiker (`arjenvangent`) met volledige
schrijfrechten. Voor de productie-versie van de PoC heeft de AI-agent een
**read-only** account nodig (analoog aan `vgbc_agent` in de Postgres-versie).
Dat moet je bij je hosting aanvragen — meestal kan dat via het cPanel/Plesk
"MySQL Users" scherm.

Tot die tijd is de tweede verdedigingslaag in `app/db.py` (de `sqlparse`-
validator die alleen SELECT-statements doorlaat) je enige beveiliging. Die
is robuust, maar minder hard dan een echte read-only databaserol.

## Wat is anders dan de Postgres-variant?

| Postgres | MySQL-port |
|---|---|
| `SERIAL` | `INT NOT NULL AUTO_INCREMENT` |
| `BOOLEAN` | `TINYINT(1)` (zelfde semantiek) |
| `NUMERIC(p,s)` | `DECIMAL(p,s)` (synoniem) |
| `DATE_TRUNC('month', d)` | `DATE_FORMAT(d, '%Y-%m-01')` |
| `DATE_TRUNC('week', d)` | `DATE_SUB(d, INTERVAL WEEKDAY(d) DAY)` |
| `TO_CHAR(d, 'YYYY-MM')` | `DATE_FORMAT(d, '%Y-%m')` |
| `CURRENT_DATE - d` (interval) | `DATEDIFF(CURDATE(), d)` |
| `FULL OUTER JOIN` | `UNION ALL` met twee `LEFT JOIN`s |
| Read-only rol via `GRANT` | Via hosting cPanel — handmatig |

## Volgende stap (na deze import)

Fase 2 is het porten van `app/db.py` van `psycopg2` naar `PyMySQL`, en de
schema-introspectie in `get_schema_context()` herschrijven (MySQL's
`information_schema` heeft een andere structuur dan Postgres'). Daarna kan de
Streamlit-app op Streamlit Community Cloud draaien tegen jouw hosting-MySQL.
