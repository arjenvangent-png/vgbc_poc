# VGBC MKB-bedrijfsassistent POC

Een lokaal draaiende AI-chatbot waarmee een MKB-ondernemer in gewone taal vragen stelt
over zijn eigen administratie — facturen, debiteuren, omzet, BTW, projectmarge en meer.

**Stack:** PostgreSQL 16 · Python · Anthropic Claude API · Streamlit

---

## Snel starten (5 stappen)

### Vereisten
- Python 3.11+
- PostgreSQL 16 (lokaal geïnstalleerd of via Docker)
- Een Anthropic API-sleutel (<https://console.anthropic.com/>)

### 1. Clone de repo

```bash
git clone https://github.com/arjenvangent-png/vgbc_poc.git
cd vgbc_poc
pip install -r requirements.txt
```

### 2. Vul `.env` in

```bash
cp .env.example .env
# Open .env en vul DATABASE_URL, AGENT_DATABASE_URL en ANTHROPIC_API_KEY in
```

### 3. Initialiseer de database (éénmalig, als postgres-superuser)

```powershell
# Windows — vervang het wachtwoord door jouw postgres-wachtwoord
$env:PGPASSWORD = 'jouw_postgres_wachtwoord'
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -f db/ddl/000_init_db.sql
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d vgbc_poc -f db/ddl/002_roles.sql
```

### 4. Laad schema én data in één keer

```powershell
.\make.ps1 seed
```

Dit genereert synthetische testdata, maakt het schema aan en laadt ~20.000 rijen.

### 5. Start de chatbot

```powershell
.\make.ps1 app
```

Open <http://localhost:8501> in je browser.

---

## Projectstructuur

```
vgbc_poc/
├── README.md
├── .env.example          # Kopieer naar .env en vul in
├── requirements.txt
├── make.ps1              # Windows-script (db-up, schema, load, seed, app, test)
├── docker-compose.yml    # Optioneel: PostgreSQL via Docker
├── db/
│   ├── ddl/
│   │   ├── 000_init_db.sql   # Database + gebruiker aanmaken (superuser)
│   │   ├── 001_schema.sql    # Tabellen, PKs, FKs, indexen
│   │   └── 002_roles.sql     # Read-only vgbc_agent-rol
│   ├── load/
│   │   └── load_csv.py       # Idempotent CSV-lader
│   └── views/
│       └── views.sql         # 7 rapportage-views
├── sample-data/
│   ├── generate_data.py      # Synthetische data-generator (Faker nl_NL)
│   └── *.csv                 # Gegenereerde testdata (in Git)
├── app/
│   ├── main.py               # Streamlit-entrypoint
│   ├── agent.py              # LLM-loop + tool-use
│   ├── db.py                 # Verbinding + veilige query-executor
│   ├── prompts/
│   │   └── system.md         # Nederlandstalige systeemprompt
│   └── logs/                 # Query-log (queries.jsonl, niet in Git)
├── tests/
│   ├── conftest.py
│   ├── test_schema.py        # Tabellen en views aanwezig?
│   ├── test_load.py          # Rij-aantallen correct?
│   └── test_db.py            # SQL-validator werkt correct?
└── docs/
    ├── ARCHITECTUUR.md
    └── DEMO-SCRIPT.md        # 8 vragen voor een klantgesprek
```

---

## Datamodel

| Tabel | Beschrijving |
|---|---|
| `klanten` | Bedrijf/particulier, NAW, BTW-nr, betaaltermijn |
| `leveranciers` | NAW, IBAN |
| `medewerkers` | Naam, rol, uurtarief |
| `producten_diensten` | Omschrijving, eenheid, prijs, BTW-tarief |
| `projecten` | Klant, status, datums, geoffreerd bedrag |
| `urenregistratie` | Project, medewerker, datum, uren |
| `facturen` | Klant, bedragen, status, creditfactuur-vlag |
| `factuurregels` | Factuur, product, aantal, bedragen |
| `betalingen` | Factuur, datum, bedrag, methode |
| `inkoopfacturen` | Leverancier, bedragen, status |

### Rapportage-views

| View | Inhoud |
|---|---|
| `v_omzet_per_maand` | Gefactureerde omzet per kalendermaand |
| `v_openstaande_debiteuren` | Openstaande verkoopfacturen met vervalcategorie |
| `v_marge_per_project` | Geoffreerd vs. gefactureerd vs. uren-kosten |
| `v_top_klanten` | Klanten gesorteerd op omzet met aandeel-% |
| `v_cashflow_per_week` | Ontvangen betalingen minus betaalde inkoopfacturen |
| `v_btw_per_kwartaal` | Af te dragen en terug te vorderen BTW per kwartaal |
| `v_openstaande_inkoopfacturen` | Te betalen leveranciersfacturen |

---

## Veiligheid

- De AI-agent gebruikt de **read-only** `vgbc_agent`-databaserol — schrijfacties zijn
  fysiek onmogelijk op databaseniveau.
- Bovendien valideert `app/db.py` elke query met `sqlparse`: alleen enkelvoudige
  SELECT-statements worden doorgelaten.
- Geen secrets in de code. Alles via `.env` (staat in `.gitignore`).

---

## Tests uitvoeren

```powershell
.\make.ps1 test
```

De testsuite controleert: schema-volledigheid, rij-aantallen na laden, en de
SQL-validator (afwijzing van DELETE/DROP/INSERT/meerdere statements).

---

## Licentie

Intern gebruik VGBC — niet voor publieke distributie.
