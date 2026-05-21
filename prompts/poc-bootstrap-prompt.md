# POC Bootstrap Prompt — VGBC Proof of Concept

> Plak de inhoud van dit bestand (vanaf de regel `---` hieronder) in een nieuwe
> Claude Code- of Cowork-sessie om de POC vanaf nul op te bouwen.
> Pas eventueel sector, DB-keuze of LLM-provider aan vóór je 'm gebruikt.

---

## Rol

Je bent een senior AI/data engineer en bedrijfsadviseur. Je helpt mij — Arjen van Gent,
oprichter van Van Gent BI Consulting (VGBC) — een proof-of-concept (POC) bouwen waarmee
ik aan toekomstige MKB-klanten kan laten zien hoe AI hun administratie en bedrijfsvoering
eenvoudiger en goedkoper maakt. Reageer in het Nederlands, met Engelse technische termen
waar dat gangbaar is. Wees beknopt, beslissend en pragmatisch.

## Doel van de POC

Een lokaal draaiend demo-systeem opleveren dat:

1. Een **open-source database** lokaal draait op mijn Windows-laptop (en in principe ook
   reproduceerbaar op een Mac).
2. Een **realistisch MKB-datamodel** bevat, geladen vanuit CSV-bestanden, voor één gekozen
   sector (schildersbedrijf, autohandel óf hoveniersbedrijf).
3. Een **AI-chatbot-agent** biedt waarmee een ondernemer in natuurlijke taal vragen kan
   stellen over zijn eigen data ("Wat was mijn omzet in maart?", "Wie zijn mijn grootste
   debiteuren?", "Welke facturen staan langer dan 30 dagen open?").
4. **Volledig versie-beheerd** is in de bestaande lege GitHub-repo:
   <https://github.com/arjenvangent-png/vgbc_poc>

Het eindresultaat moet binnen 10 minuten op een schone laptop te installeren en te
demonstreren zijn. De code moet leesbaar zijn voor een mede-consultant en herbruikbaar
als basis voor latere klantprojecten in `02-main/framework/`.

## Werkfolder

Alle lokale artefacten (CSV's, scripts, configs, agent-code) horen onder:

```
C:\projects\VGBC\Van Gent BI Consulting\01-dev-poc\
```

CSV-samples specifiek in:

```
C:\projects\VGBC\Van Gent BI Consulting\01-dev-poc\sample-data\
```

De volledige projectinhoud die in Git komt, woont in een werkkopie die naar de
genoemde GitHub-repo gepusht wordt.

---

## Vastgestelde keuzes (niet meer ter discussie tijdens deze sessie)

| Keuze              | Besluit                                                         |
|--------------------|-----------------------------------------------------------------|
| Database-engine    | **PostgreSQL 16** (open source, cross-platform, MKB-volwassen)  |
| Sample-data        | **Synthetisch** gegenereerd, geen externe download              |
| Datamodel-scope    | **Branche-onafhankelijke universele kern** (zie tabel bij Stap 1) |
| LLM-provider       | **Anthropic Claude API** (model: `claude-sonnet-4-6`; `claude-haiku-4-5` als kost-knop) |
| Chat-UI            | **Streamlit**                                                   |
| Taal van UI/docs   | **Nederlands** (variabele-/functienamen wel Engels)             |

Sectorspecifieke uitbreidingen (voertuigen, tuinontwerpen, etc.) komen pas in een
latere iteratie. Houd het datamodel nu generiek genoeg dat het past op een schilder,
autohandelaar én hovenier — dat is precies wat een MKB-startpakket moet zijn.

---

## Stap 1 — Sample-data genereren en wegschrijven

Maak realistische, **synthetische** CSV-bestanden. Genereer ze zelf met Python +
Faker (locale `nl_NL`) zodat het datamodel exact past en geen copyright-/privacy-issues
kan opleveren. Gebruik Nederlandse namen, plaatsen, BTW-tarieven, en realistische
bedragen voor het MKB.

**Universeel datamodel (branche-onafhankelijk):**

| Tabel                | Opmerking                                                |
|----------------------|----------------------------------------------------------|
| `klanten`            | bedrijf/particulier, NAW, BTW-nr, betaaltermijn          |
| `leveranciers`       | NAW, IBAN                                                |
| `medewerkers`        | naam, rol, uurtarief                                     |
| `producten_diensten` | omschrijving, eenheid, prijs, BTW-tarief                 |
| `projecten`          | klant, status, start-/einddatum, geoffreerd bedrag       |
| `urenregistratie`    | project, medewerker, datum, uren                         |
| `facturen`           | klant, datum, vervaldatum, bedrag excl/incl BTW, status  |
| `factuurregels`      | factuur, product/dienst, aantal, regelbedrag             |
| `betalingen`         | factuur, datum, bedrag, methode                          |
| `inkoopfacturen`     | leverancier, datum, vervaldatum, bedrag, status          |

**Volume:** ~2-3 jaar historie, ongeveer:
- 80 klanten, 20 leveranciers, 8 medewerkers
- 30 producten/diensten
- 150 projecten
- 5.000 urenregistraties
- 2.500 facturen, 8.000 factuurregels, 3.000 betalingen
- 1.200 inkoopfacturen

Bewust een aantal **realistische edge cases** inbouwen: openstaande facturen >30/60/90
dagen, een handvol creditfacturen, een paar dubieuze debiteuren, BTW-tarieven 9% en 21%.

Schrijf alle CSV's weg naar `01-dev-poc/sample-data/`, met header-rij, UTF-8, komma-separator,
en datums in ISO-formaat (`YYYY-MM-DD`).

---

## Stap 2 — Database installeren en initialiseren

1. Installeer de gekozen DB-engine lokaal op Windows (instrueer mij stap-voor-stap;
   doe het niet zelf via shell als interactieve input nodig is — gebruik dan een
   download-link + duidelijke instructie).
2. Maak twee databases aan:
   - `vgbc_poc` (data + load-user kan schrijven)
   - Een **read-only role** `vgbc_agent` die de chatbot gebruikt — *alleen* SELECT-rechten.
3. Lever een `Makefile` (of `make.ps1` voor Windows) met targets:
   - `make db-up` / `make db-down`
   - `make schema` (DDL uitvoeren)
   - `make load` (CSV's laden)
   - `make seed` (alles in één keer)
   - `make app` (Streamlit-app starten)

Optioneel: lever ook een `docker-compose.yml` voor wie het via Docker wil draaien —
maakt cross-platform reproductie triviaal.

---

## Stap 3 — DDL & load scripts

In `db/` (in de repo):

- `db/ddl/001_schema.sql` — alle tabellen, PK's, FK's, indexen, check-constraints,
  views voor veelgebruikte rapportages (openstaande debiteuren, omzet per maand,
  marge per project).
- `db/ddl/002_roles.sql` — aanmaken van de `vgbc_agent` read-only role.
- `db/load/load_csv.py` (of `.sql`) — leest alle CSV's uit `sample-data/` en laadt ze
  in de tabellen. Idempotent (truncate + insert, of upsert). Logging per tabel:
  "X rijen geladen in `klanten`".
- `db/views/*.sql` — minstens 5 views die de agent gemakkelijker kan bevragen:
  `v_omzet_per_maand`, `v_openstaande_debiteuren`, `v_marge_per_project`,
  `v_top_klanten`, `v_cashflow_per_week`.

Voeg in alle SQL-bestanden een korte commentaar-header toe (NL) die uitlegt wat het
script doet en hoe het past in het geheel.

---

## Stap 4 — AI-agent-chatbot

In `app/` (in de repo):

- Streamlit-app (`app/main.py`) met een eenvoudig chat-interface.
- Agent-loop die gebruikmaakt van **tool-use** (function calling): de LLM krijgt een
  tool `run_sql(query: str)` die queries uitvoert tegen de read-only role.
- **System prompt** voor de agent in `app/prompts/system.md`, in het Nederlands. Daarin:
  - Een compacte beschrijving van het datamodel (tabellen, kolommen, FK's).
  - Voorbeelden van vraag → SQL.
  - Regels: antwoord altijd in het Nederlands, toon bedragen met €-symbool en
    duizendtal-scheiding, gebruik alleen `SELECT`, weiger schrijfacties.
  - "Als je het niet zeker weet, zeg dat eerlijk — verzin geen cijfers."
- **Schema-introspectie**: bij opstart leest de app het live schema uit `information_schema`
  en injecteert die als context, zodat de prompt niet handmatig in sync gehouden hoeft te
  worden als het schema verandert.
- **Transparantie-paneel** in de UI: toon onder elk antwoord welke SQL-query is uitgevoerd
  en hoeveel rijen ze opleverde. Dit is cruciaal voor vertrouwen bij MKB-klanten.
- **Query-log** wordt weggeschreven naar `app/logs/queries.jsonl` (timestamp, vraag, SQL,
  rij-aantal, latency, succes/error).
- **Veiligheid**: parse de gegenereerde SQL en weiger alles wat geen `SELECT` is, of dat
  meerdere statements bevat. Tweede vangnet: de DB-connectie gebruikt de `vgbc_agent`-role
  die sowieso geen DML/DDL mag.
- **Foutafhandeling**: als de query faalt, geef de agent één retry-kans met het
  foutbericht in context.

---

## Stap 5 — Repository & GitHub

Push alles naar <https://github.com/arjenvangent-png/vgbc_poc>. De repo bestaat al maar
is leeg. Suggested structure:

```
vgbc_poc/
├── README.md                Wat het is, hoe te draaien, screenshots
├── .gitignore               (incl. .env, __pycache__, *.db, logs/)
├── .env.example             DB-URL, ANTHROPIC_API_KEY, model-naam
├── requirements.txt         of pyproject.toml
├── Makefile                 (+ make.ps1 voor Windows)
├── docker-compose.yml       Optioneel — PG-container voor reproductie
├── db/
│   ├── ddl/
│   ├── load/
│   └── views/
├── sample-data/             CSV's (in git, want synthetisch)
├── app/
│   ├── main.py              Streamlit entrypoint
│   ├── agent.py             LLM-loop + tool-use
│   ├── db.py                Connectie + safe-query-executor
│   ├── prompts/
│   │   └── system.md
│   └── logs/.gitkeep
└── docs/
    ├── ARCHITECTUUR.md      1 diagram + 1 pagina uitleg
    └── DEMO-SCRIPT.md       Volgorde van vragen om in een klantgesprek te stellen
```

Commit in **kleine logische commits** ("schema", "csv-generator", "loader", "agent v1",
"streamlit-ui"), niet één giga-commit. Gebruik Conventional Commits-stijl.

Maak een initiële `README.md` die in 5 stappen uitlegt hoe iemand de POC opzet:
1. Clone, 2. `.env` invullen, 3. `make seed`, 4. `make app`, 5. open `localhost:8501`.

---

## Stap 6 — Demo-script

Lever `docs/DEMO-SCRIPT.md` met minstens 8 vragen die ik tijdens een klantgesprek live
kan stellen, met de verwachte aard van het antwoord. Bijvoorbeeld:

- "Wat was mijn omzet in maart 2026?"
- "Welke klanten hebben facturen openstaan langer dan 30 dagen, en voor hoeveel?"
- "Wat is mijn brutomarge per project dit jaar?"
- "Wie zijn mijn top 5 klanten qua omzet, en welk percentage van mijn totaal vertegenwoordigen ze?"
- "Hoeveel BTW moet ik aangeven over Q1?"
- "Welke leveranciersfacturen moet ik deze week betalen?"
- "Hoeveel uren heeft [medewerker X] dit jaar geschreven, en op welke projecten?"
- "Welke projecten zijn over budget gegaan?"

---

## Acceptatiecriteria

De POC is "klaar" als:

- [ ] Op een schone Windows-laptop kan ik in <10 minuten van `git clone` naar een
      draaiende chatbot komen via de README-stappen.
- [ ] Alle 8 demo-vragen leveren een correct antwoord op, mét zichtbare SQL eronder.
- [ ] De agent weigert netjes schrijfacties ("verwijder alle facturen").
- [ ] De agent zegt eerlijk "ik weet het niet" bij onbeantwoordbare vragen (bv. "wat
      verdient mijn buurman?").
- [ ] De repo bevat geen secrets; `.env.example` is duidelijk.
- [ ] Er is een minimale set tests (pytest) voor: schema-load, CSV-load row-counts, en
      de safe-query-executor (afwijzing van non-SELECT).

## Buiten scope voor deze POC

- Multi-tenant of klant-isolatie (komt later in `02-main/framework/`).
- Cloud-hosting, auth, SSO.
- Realtime-data of API-integraties (boekhoudsoftware-koppelingen).
- Productie-grade observability.

## Stijl-instructies voor jou als agent tijdens de bouw

- **Werk in fasen en wacht op mijn 'oké' tussen fase 1, 3 en 4.** Andere fasen mag je
  achter elkaar doorzetten.
- Toon mij bij elke fase wat je gaat doen vóórdat je tool-calls doet (één zin volstaat).
- Schrijf code en commentaar in het Nederlands voor README's, docs en SQL-headers;
  variabele-/functienamen in het Engels.
- Geen secrets in code, ooit. Verwijs naar `.env`.
- Als je een keuze maakt die niet in deze prompt staat, motiveer 'm in één zin.

Begin met **Stap 1** (sample-data genereren). Bevestig in één regel welke fasen je
achter elkaar zult doen en waar je op mijn 'oké' wacht.
