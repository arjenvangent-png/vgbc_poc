# Security & misbruik-bescherming voor de online demo

De PoC is een **publieke** chatbot waarbij elke vraag een betaalde
Anthropic-API call veroorzaakt. Zonder bescherming kan één hostile gebruiker
of bot een hoge factuur achterlaten. Dit document beschrijft wat er
**standaard aan staat**, welke extra lagen je **kunt aanzetten**, en hoe het
in het ergste geval uitpakt qua kosten.

---

## Lagen overzicht

```
┌──────────────────────────────────────────────────────────────────┐
│ Laag 1: robots.txt + meta noindex                                │ ← Zoekmachines
│         Zoekmachines en AI-crawlers vinden /demo niet            │   buiten houden
├──────────────────────────────────────────────────────────────────┤
│ Laag 2: Klik-om-te-laden gate op vgbc.nl/demo.html               │ ← Passieve
│         Iframe laadt pas na een knop-klik                        │   bots filter
├──────────────────────────────────────────────────────────────────┤
│ Laag 3: Optioneel — Cloudflare Turnstile op /demo.html           │ ← Actieve
│         Echte mens-verificatie (vink-vrij)                       │   bots filter
├──────────────────────────────────────────────────────────────────┤
│ Laag 4: Per-sessie rate limit in Streamlit-app                   │ ← Cost cap
│         20 vragen/uur, 3s tussen vragen                          │
├──────────────────────────────────────────────────────────────────┤
│ Laag 5: Optioneel — wachtwoord-gate op Streamlit-app             │ ← Alleen
│         st.secrets["demo_password"]                              │   voor genodigden
├──────────────────────────────────────────────────────────────────┤
│ Laag 6: SQL-validator in app/db.py                               │ ← Database
│         Weigert alles wat geen enkelvoudig SELECT is             │   bescherming
└──────────────────────────────────────────────────────────────────┘
```

Laag 1, 2, 4 en 6 staan **automatisch aan** na deployment. Laag 3 en 5 zijn
opt-in en hieronder beschreven.

---

## Laag 1 — Zoekmachines & AI-crawlers afweren (AAN)

**Wat is er geregeld:**
- `website/robots.txt` zet `Disallow: /demo.html` voor alle bots.
- AI-crawlers (`GPTBot`, `ClaudeBot`, `CCBot`, `Google-Extended`, `PerplexityBot`,
  `Bytespider`, etc.) krijgen `Disallow: /` voor de hele site — onze
  marketing-tekst wordt niet zonder toestemming in een trainingsset gestopt.
- `demo.html` heeft `<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">`.

**Wat het wel doet:** zorgt dat de demo niet via Google/Bing vindbaar wordt
of in een AI-zoekresultaat verschijnt.

**Wat het niet doet:** stopt geen gerichte aanvallen. Iemand die de URL
direct kent kan nog steeds binnenkomen.

---

## Laag 2 — Klik-om-te-laden gate (AAN)

**Wat is er geregeld:** de `<iframe>` op `/demo.html` heeft geen `src`-
attribuut bij pageload. Pas wanneer de bezoeker op de "Start de demo" knop
klikt, zet JavaScript de URL erin. Bots die enkel HTML parseren (zoals de
meeste scrapers) zien dus nooit de Streamlit-app, en triggeren ook geen
laad-verkeer naar Streamlit Cloud.

**Wat het wel doet:** filtert >90% van geautomatiseerd verkeer.

**Wat het niet doet:** stopt geen headless browser (Puppeteer, Playwright)
die wel JavaScript draait. Daarvoor heb je laag 3 en 4 nodig.

---

## Laag 3 — Cloudflare Turnstile (OPTIONEEL)

Turnstile is Cloudflare's gratis alternatief voor reCAPTCHA: het verifieert
"echte mens" zonder dat de gebruiker een vinkje hoeft te zetten. Werkt
onzichtbaar in 95% van de gevallen.

### Setup (15 min eenmalig)

1. **Cloudflare-account aanmaken** (gratis): <https://dash.cloudflare.com/sign-up>.
2. **Domein toevoegen**: voeg `vgbc.nl` toe als "Site" (Free plan).
3. **Nameservers wijzigen** bij je domein-registrar (waar je `vgbc.nl`
   geregistreerd hebt) naar Cloudflare's nameservers. Cloudflare laat je
   zien welke twee dat zijn. Dit kost een paar uur DNS-propagatie.
4. **Turnstile widget aanmaken**:
   - Ga naar <https://dash.cloudflare.com/?to=/:account/turnstile>
   - Klik "Add site"
   - Domain: `vgbc.nl`
   - Widget type: **Managed** (Cloudflare beslist wel/niet vink-uitdaging)
   - Pre-Clearance for: alleen `vgbc.nl` (niet `*.streamlit.app`)
5. **Kopieer de Site Key** (begint met `0x4AAAAAA...`).

### Activeren in demo.html

Open `website/demo.html` en zoek het commentaar-blok
`OPTIONEEL: Cloudflare Turnstile`. Vervang het uitgecommentarieerde JS-blok
door:

```html
<!-- In de <head>: -->
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>

<!-- In demoGate, vóór de "Start de demo" button: -->
<div class="cf-turnstile"
     data-sitekey="JOUW_SITE_KEY_HIER"
     data-callback="onTurnstileSuccess"
     data-theme="light"></div>

<!-- En de button-handler aanpassen: -->
<script>
    var turnstileToken = null;
    function onTurnstileSuccess(token) {
        turnstileToken = token;
        document.getElementById('loadDemoBtn').disabled = false;
    }
    document.getElementById('loadDemoBtn').disabled = true;
    // De bestaande btn.addEventListener-handler kan blijven; bots krijgen
    // de knop niet werkend zonder turnstileToken.
</script>
```

Resultaat: bezoekers moeten een (meestal onzichtbare) challenge passeren
voordat ze de demo-iframe kunnen laden.

> Belangrijk: server-side validatie van het Turnstile-token kun je niet doen
> bij een statische hosting. Voor de demo is **client-side** verificatie
> voldoende — het stopt geautomatiseerde bots, niet een mens die de site
> source-code analyseert. Voor de echte productie (bv. een endpoint dat
> direct geld kost) zou je server-side validatie willen.

---

## Laag 4 — Per-sessie rate limit (AAN)

**Wat is er geregeld:** `app/main.py` houdt per Streamlit-sessie bij hoeveel
vragen je stelt en wanneer:

- Maximaal **20 vragen per uur per sessie** (`RATE_LIMIT_MAX_QUERIES=20`)
- Minimaal **3 seconden tussen vragen** (`RATE_LIMIT_MIN_INTERVAL_S=3`)
- Venster van **1 uur** (`RATE_LIMIT_WINDOW_S=3600`)

Bij overschrijden krijgt de gebruiker een Nederlands-vriendelijke melding
met een CTA naar `vgbc.nl/contact.html`. Geen 500-fout, geen technische
melding.

### Configureren via Streamlit secrets

In Streamlit Cloud → Manage app → Secrets:

```toml
# Strenger maken (10/uur):
RATE_LIMIT_MAX_QUERIES = "10"

# Helemaal uitzetten (niet aanbevolen):
RATE_LIMIT_MAX_QUERIES = "0"

# Langer wachten tussen vragen (anti-button-spam):
RATE_LIMIT_MIN_INTERVAL_S = "5"
```

### Beperkingen

Streamlit's session state is **per browser-sessie**. Een hostile gebruiker
die elke 20 vragen zijn browser-cookies wist of een incognito-venster opent,
kan de limiet omzeilen. Daarom de combinatie met laag 1-3.

Voor échte IP-rate-limiting heb je een edge-proxy nodig (Cloudflare WAF
custom rule, of een server tussen client en Streamlit). Voor de demo is
sessie-niveau voldoende — een gemotiveerde aanvaller die elke 20 vragen
zijn IP wisselt is geen normaal misbruik-profiel.

---

## Laag 5 — Wachtwoord-gate op Streamlit (OPTIONEEL)

Als je de demo alleen aan **uitgenodigde prospects** wilt laten zien, voeg
dan een simpel wachtwoord toe in `app/main.py`. Streamlit's eigen pattern:

```python
import hmac

def check_password() -> bool:
    """Toont een password-input en blokkeert de app tot het correct is."""
    def password_entered():
        if hmac.compare_digest(
            st.session_state["password"], st.secrets["demo_password"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "Wachtwoord (vraag een toegangscode aan via arjen.van.gent@gmail.com)",
        type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("Onjuist wachtwoord — probeer opnieuw.")
    return False

# Bovenaan main.py, na st.set_page_config:
if not check_password():
    st.stop()
```

En in Streamlit secrets:
```toml
demo_password = "een_simpel_wachtwoord_dat_je_per_email_deelt"
```

**Wanneer dit zinvol is:**
- Je deelt de demo expliciet met een handvol prospects per maand
- De drempel "moet wachtwoord opvragen" is geen probleem voor je
  conversie-funnel

**Wanneer NIET:**
- Je wilt dat bezoekers vanaf vgbc.nl gewoon kunnen klikken en spelen.
  Eén extra password-prompt verlaagt conversie aanzienlijk.

---

## Laag 6 — SQL-validator (AAN, kern van de PoC)

Zit al in `app/db.py`: `validate_query()` parse-checkt elke SQL via
`sqlparse` en weigert:
- Niet-SELECT statements (INSERT/UPDATE/DELETE/DROP/etc.)
- Meerdere statements gescheiden door `;`

Plus: op Neon draait de Streamlit-app als de **read-only rol `vgbc_agent`**
(zie deploy-runbook stap 4). Dus zelfs als de validator omzeild zou worden,
weigert Neon nog steeds elke schrijfactie op DB-niveau. Tweelaagse defense.

---

## Worst-case kostenmodel

Stel een hostile gebruiker probeert maximaal misbruik te maken:

| Scenario | Wat ze doen | Max kosten per dag |
|---|---|---|
| Eén browser, geen tricks | 20 vragen × 24 uur (limiet) | 480 × €0,03 = **€14,40** |
| Incognito-venster spam | Elke 20 vragen nieuwe sessie, doorgaan | Onbeperkt zonder Turnstile |
| Met Turnstile aan | Elke 20 vragen nieuwe captcha | ~50-100 vragen/uur max realistisch |
| Met password + Turnstile | Alleen genodigden | Praktisch onmogelijk |

**Mijn aanbeveling voor de huidige fase:**
- Begin met **laag 1, 2, 4** (al actief na deployment)
- Voeg **laag 3 (Turnstile)** toe binnen de eerste week
- Houd **laag 5 (password)** achter de hand voor wanneer je de demo
  pro-actief in een nieuwsbrief of LinkedIn-post deelt — dan komt er meer
  random verkeer langs

---

## Monitoring — weten wanneer iets fout gaat

Anthropic Console heeft een **billing dashboard** met dagelijks verbruik.
Stel daar een **spend alert** in op bv. €5/dag:

1. <https://console.anthropic.com/settings/billing> → "Spend Limits"
2. Soft alert op €5/dag, hard alert + stop op €20/dag

Verder geeft `app/logs/queries.jsonl` (op Streamlit Cloud ephemeral — leeft
zolang de container leeft) inzicht in welke queries echt worden gedraaid.
Voor permanente logging zou je naar een externe service (Sentry, Logtail)
moeten schrijven — voor de demo niet nodig.

---

## Snelle checklist voor go-live

- [ ] `robots.txt` op vgbc.nl staat (laag 1)
- [ ] `demo.html` heeft noindex meta en klik-gate (laag 1+2)
- [ ] `app/main.py` rate-limit code aanwezig (laag 4)
- [ ] Op Streamlit Cloud: `RATE_LIMIT_*` secrets ingesteld (of weggelaten
      → defaults uit code worden gebruikt)
- [ ] Op Neon: `vgbc_agent` read-only rol bestaat, `AGENT_DATABASE_URL`
      gebruikt deze rol (laag 6)
- [ ] Anthropic Console: spend alert ingesteld
- [ ] (Optioneel) Cloudflare Turnstile actief (laag 3)
- [ ] (Optioneel) Demo-password ingesteld (laag 5)
