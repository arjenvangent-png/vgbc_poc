# Deployment-runbook: VGBC PoC online

Doel: dezelfde PoC die lokaal draait toegankelijk maken via
`https://www.vgbc.nl/demo.html` — de demo zelf draait op
**Streamlit Community Cloud** (gratis) tegen **Neon serverless Postgres**
(gratis tier, 0,5 GB).

Geschatte tijd: 30-45 minuten als alles meezit.

---

## Architectuur

```
[bezoeker]
   │
   ▼
www.vgbc.nl/demo.html        ← jouw bestaande hosting (statische iframe-pagina)
   │  iframe src
   ▼
vgbc-poc.streamlit.app       ← Streamlit Community Cloud (gratis)
   │  psycopg2 + SSL
   ▼
xxx.eu-central-1.aws.neon.tech ← Neon Postgres (gratis tier, EU-regio)
```

---

## Vóór je begint

Aanmelden bij beide diensten — gratis, geen creditcard nodig:

- **Neon**: <https://console.neon.tech/> — login met GitHub of e-mail
- **Streamlit Community Cloud**: <https://streamlit.io/cloud> — verplicht
  GitHub-login, want het deployt vanuit een repo

Beide moet je **dezelfde GitHub-account** gebruiken die ook eigenaar is van
`arjenvangent-png/vgbc_poc` (anders kan Streamlit je repo niet zien).

Open daarnaast een PowerShell-venster in de PoC-map:

```powershell
cd "C:\projects\VGBC\Van Gent BI Consulting\01-dev-poc"
```

---

## Stap 1 — Neon project aanmaken (5 min)

1. Login op <https://console.neon.tech/>.
2. **Create project**:
   - Project name: `vgbc-poc`
   - Postgres version: 16
   - Region: **EU Central (Frankfurt)** ← belangrijk i.v.m. latency naar
     Streamlit Cloud en data-soevereiniteit
   - Database name: laat default `neondb` staan (we maken `vgbc_poc` zelf aan)
3. Na klikken op Create krijg je een **Connection string** te zien — kopieer
   die. Hij ziet er ongeveer zo uit:
   ```
   postgresql://neondb_owner:abc123XYZ@ep-cool-name-12345.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
4. **Bewaar deze string veilig** (KeePass, 1Password, of in een onderling
   beveiligd notitiesysteem). Niet in chat plakken, niet in git committen.

> Tip: Neon's free tier slaapt na 5 minuten inactiviteit. Eerste query na
> "wakker worden" duurt ~1-2 seconden extra. Voor een demo prima.

---

## Stap 2 — Lokale data dumpen naar SQL (5 min)

We exporteren je werkende lokale database (schema + alle ~20.000 rijen) naar
één SQL-bestand. Dat is straks de bron voor de Neon-import.

In PowerShell, vanaf de PoC-map:

```powershell
# Vervang het wachtwoord door je lokale vgbc_user wachtwoord uit .env
$env:PGPASSWORD = 'JOUW_LOKALE_POSTGRES_WACHTWOORD'

# Volledige dump: schema + views + data, in één bestand
& "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" `
    -U vgbc_user `
    -h localhost `
    -d vgbc_poc `
    --no-owner `
    --no-privileges `
    --file db\neon_dump.sql
```

Resultaat: `db\neon_dump.sql` (geschat ~3-5 MB).

> `--no-owner` en `--no-privileges` voorkomen dat de dump verwijst naar de
> lokale `vgbc_user` rol die op Neon niet bestaat.

Optioneel: open `db\neon_dump.sql` even in een editor en controleer dat het
begint met `CREATE TABLE` statements (geen rare encoding-fouten).

---

## Stap 3 — Database in Neon aanmaken en dump importeren (5 min)

Eerst de eigenlijke database aanmaken op Neon (de standaard `neondb` laten we
voor wat hij is):

```powershell
# Plak hier de connection string van Neon (uit stap 1), maar
# WIJZIG '/neondb?' aan het eind naar '/postgres?' — we connecten eerst
# naar de admin-database om een nieuwe DB te kunnen aanmaken.
$NEON_ADMIN = 'postgresql://neondb_owner:WACHTWOORD@HOSTNAME/postgres?sslmode=require'

# Database aanmaken
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" $NEON_ADMIN -c "CREATE DATABASE vgbc_poc"
```

Daarna de dump erin laden. Pas de connection string weer aan: vervang
`/postgres?` door `/vgbc_poc?`:

```powershell
$NEON_VGBC = 'postgresql://neondb_owner:WACHTWOORD@HOSTNAME/vgbc_poc?sslmode=require'

& "C:\Program Files\PostgreSQL\16\bin\psql.exe" $NEON_VGBC -f db\neon_dump.sql
```

Verwacht: een lange stroom `CREATE TABLE`, `CREATE INDEX`, `COPY ... 81`,
`COPY ... 2500`, etc. — geen rode `ERROR` regels (gele `NOTICE` zijn OK).

Controleer met:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" $NEON_VGBC -c "SELECT table_name, (SELECT COUNT(*) FROM klanten) AS aantal FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' LIMIT 3"
```

Of via Neon's web-SQL-editor: <https://console.neon.tech/> → jouw project →
SQL Editor → tabel-namen moeten links verschijnen.

---

## Stap 4 — Read-only user op Neon (3 min)

In tegenstelling tot je shared hosting kan dit op Neon wél. Plak in Neon's
SQL Editor:

```sql
-- Read-only rol aanmaken
CREATE ROLE vgbc_agent LOGIN PASSWORD 'kies_een_apart_sterk_wachtwoord_voor_de_agent';

-- Connect-rechten
GRANT CONNECT ON DATABASE vgbc_poc TO vgbc_agent;

-- Lees-rechten op alle bestaande tabellen en views
GRANT USAGE ON SCHEMA public TO vgbc_agent;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO vgbc_agent;

-- Ook op toekomstige tabellen
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO vgbc_agent;
```

Test de read-only rol door een SELECT te draaien (moet lukken) en een DELETE
(moet falen):

```sql
SELECT COUNT(*) FROM klanten;
-- Verwacht: 80

DELETE FROM klanten WHERE klant_id = 1;
-- Verwacht: ERROR: permission denied for table klanten
```

Bouw nu twee connection strings die je straks nodig hebt:

- **DATABASE_URL** (schrijfgebruiker — alleen voor onderhoud/herstart):
  ```
  postgresql://neondb_owner:WACHTWOORD@HOSTNAME/vgbc_poc?sslmode=require
  ```
- **AGENT_DATABASE_URL** (read-only, voor de Streamlit-app):
  ```
  postgresql://vgbc_agent:AGENT_WACHTWOORD@HOSTNAME/vgbc_poc?sslmode=require
  ```

---

## Stap 5 — GitHub repo bijwerken (2 min)

Streamlit Cloud deployt direct vanuit GitHub, dus alle code moet daar staan
en up-to-date zijn. Vanaf de PoC-map:

```powershell
git status              # check wat er nog niet gecommit is
git add .
git commit -m "Klaar voor Streamlit Cloud deployment"
git push origin main
```

Open daarna <https://github.com/arjenvangent-png/vgbc_poc> in je browser en
controleer dat `app/main.py`, `app/agent.py`, `app/db.py`, `app/prompts/`,
en `requirements.txt` allemaal aanwezig zijn.

> Belangrijk: `.env` mag NIET in de repo staan (zit in `.gitignore`).
> `db/neon_dump.sql` zou ik ook in `.gitignore` zetten — bevat alle data en
> hoeft niet in git.

---

## Stap 6 — Streamlit Cloud deploy (5 min)

1. Login op <https://share.streamlit.io/>.
2. Klik **New app** (rechtsboven).
3. Vul in:
   - Repository: `arjenvangent-png/vgbc_poc`
   - Branch: `main`
   - Main file path: `app/main.py`
   - App URL: `vgbc-poc` (wordt `vgbc-poc.streamlit.app`)
4. Klik **Advanced settings** → **Secrets**. Plak hier (TOML-formaat):

```toml
ANTHROPIC_API_KEY = "sk-ant-jouw-echte-sleutel-hier"
DATABASE_URL = "postgresql://neondb_owner:WACHTWOORD@HOSTNAME/vgbc_poc?sslmode=require"
AGENT_DATABASE_URL = "postgresql://vgbc_agent:AGENT_WACHTWOORD@HOSTNAME/vgbc_poc?sslmode=require"
LLM_MODEL = "claude-sonnet-4-6"
```

5. Klik **Deploy**.
6. Wacht ~2-3 minuten — Streamlit installeert dependencies en start de app.

Verwacht: app verschijnt op `https://vgbc-poc.streamlit.app/`. Test door één
van de voorbeeldvragen aan te klikken in de sidebar.

> Als er een fout komt: klik op "Manage app" → "Logs" om te zien wat er mis
> ging. Meest voorkomende oorzaken: vergeten secret, typo in connection string,
> of `via.placeholder.com` URL in `main.py` (zie hieronder).

---

## Stap 7 — Bekende kleine issue: placeholder-image

`app/main.py` regel 52 verwijst naar `https://via.placeholder.com/200x60` —
die service is offline. De app crasht hierdoor niet, maar je sidebar toont
een gebroken-afbeelding-icoontje.

Snelle fix: verwijder die regel of vervang door tekst:

```python
# Verwijder:
st.image("https://via.placeholder.com/200x60?text=VGBC", width=200)

# Of vervang door:
st.markdown("### VGBC")
```

Voor een nettere oplossing: upload `media/logo/vgbc-logo.png` (of een PNG die
je kiest) naar de repo onder `app/assets/`, en gebruik:

```python
st.image("assets/vgbc-logo.png", width=200)
```

Niet kritiek — kan ook later.

---

## Stap 8 — vgbc.nl koppelen via iframe (5 min)

Het bestand `demo.html` ligt al klaar in de website-map. Twee dingen
controleren vóór upload:

1. Open `demo.html` en kijk of de iframe-URL klopt:
   ```html
   src="https://vgbc-poc.streamlit.app/?embed=true&embed_options=light_theme,hide_loading_screen"
   ```
   Als je een andere app-naam hebt gekozen in stap 6, pas die hier aan.

2. Upload **alle vier de HTML-bestanden** (`index.html`, `diensten.html`,
   `demo.html`, `contact.html`) en het CSS naar de root van je hosting via
   FTP (IP `45.82.191.102`, gebruiker `xrfxdlxg`). De andere drie heb ik
   bijgewerkt met de nieuwe nav-link "Demo".

Test: open `https://www.vgbc.nl/demo.html`. De Streamlit-app moet onder de
intro-tekst verschijnen in een ingelijst kader.

> **Mocht het iframe niet laden** met een melding als "weigerde verbinding"
> of "X-Frame-Options": Streamlit Cloud zou iframes met `?embed=true` moeten
> toestaan, maar als het niet werkt is de fallback al ingebouwd — bezoekers
> zien dan een knop "Open in nieuw tabblad" en kunnen via de directe URL
> verder.

---

## Stap 9 — Test op verschillende devices

- Desktop (Chrome, Firefox, Safari): test op een wide screen
- Telefoon: de iframe is `80vh` hoog, dat past meestal goed
- Test 2-3 voorbeeldvragen vanaf vgbc.nl/demo.html en kijk of antwoorden
  kloppen

---

## Kosten-overzicht

| Onderdeel | Tier | Kosten |
|---|---|---|
| Neon Postgres | Free | €0/mnd · 0,5 GB storage · auto-suspend na 5 min |
| Streamlit Cloud | Community | €0/mnd · 1 publieke app · onbeperkt requests |
| Anthropic API | pay-as-you-go | ~€0,01-0,05 per vraag (Sonnet 4.6) |
| Bestaande VGBC hosting | (al betaald) | €0 extra |

Bij honderd vragen per maand: **~€1-5/mnd**, voornamelijk Claude API.

---

## Wat te doen bij problemen

1. **App start niet** → Streamlit Cloud → Manage app → Logs lezen
2. **Database connection error** → Neon dashboard → controleer of project niet
   gesuspendeerd is, herstart eventueel
3. **"Anthropic API error"** → controleer of de API-key in Streamlit secrets
   nog werkt op <https://console.anthropic.com/>
4. **Iframe blijft leeg op vgbc.nl** → open browser console (F12 → Console),
   kijk naar X-Frame-Options of CSP-foutmeldingen
5. **Trage eerste vraag** → Neon's cold start. Stuur eerst een dummy-query
   via Neon's SQL Editor om de DB wakker te maken vóór je een klant laat
   kijken.

---

## Volgende stappen (later)

- **Custom subdomein** `demo.vgbc.nl`: vereist een redirect bij je hosting
  naar `vgbc-poc.streamlit.app`. Free tier Streamlit Cloud ondersteunt geen
  custom domains direct. Met een 302-redirect bij je hosting is het wel
  oplosbaar — vraag het hosting-paneel om een redirect aan te maken.
- **Anonimiseer demo-data verder** als je het breed wilt delen: de huidige
  namen zijn al fictief (Faker `nl_NL`), maar je kunt extra opvallende velden
  generaliseren als "Klant 1", "Klant 2".
- **Rate limiting** op de Streamlit-app: free tier heeft geen built-in auth.
  Als een grappenmaker veel API-calls doet, betaal jij voor de Claude-calls.
  Optie: voeg een simpel wachtwoord toe via `streamlit-authenticator`, of
  zet de demo achter een eenvoudige basic-auth in Cloudflare (gratis).
