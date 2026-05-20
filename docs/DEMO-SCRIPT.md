# Demo-script — VGBC MKB-bedrijfsassistent

Gebruik dit script tijdens een klantgesprek om de POC live te demonstreren.
Stel de vragen in de chatbot terwijl de klant meekijkt — toon altijd het
SQL-transparantie-paneel zodat duidelijk is dat de assistent échte data ophaalt.

---

## Voorbereiding (voor het gesprek)

1. Open terminal: `.\make.ps1 app` → wacht tot Streamlit opstart
2. Open browser: <http://localhost:8501>
3. Kies model: **claude-sonnet-4-6** (kwaliteit) of haiku (snelheid)

---

## De 8 demo-vragen

### 1. Omzetoverzicht
**Stel in:** "Wat was mijn omzet in maart 2026?"

**Verwacht antwoord:** Totale gefactureerde omzet (excl. BTW), BTW-bedrag en incl.-BTW
voor de maand maart 2026, opgehaald uit `v_omzet_per_maand`.

**Verkooppunt:** *"Dit is precies de vraag die een ondernemer elke maand stelt aan zijn
boekhouder — nu krijg je het antwoord in 3 seconden, zelf, zonder tussenkomst."*

---

### 2. Openstaande debiteuren
**Stel in:** "Welke klanten hebben facturen openstaan langer dan 30 dagen,
en voor hoeveel?"

**Verwacht antwoord:** Een tabel met klantnaam, factuurnummer, vervalcategorie
(0–30 / 31–60 / 61–90 / >90 dagen) en openstaand bedrag. Dubieuze debiteuren
worden gemarkeerd.

**Verkooppunt:** *"Geen Excel meer bijhouden — de assistent ziet live welke klanten
al weken niet betaald hebben."*

---

### 3. Top-klanten
**Stel in:** "Wie zijn mijn top 5 klanten qua omzet, en welk percentage van
mijn totale omzet vertegenwoordigen ze?"

**Verwacht antwoord:** Top 5 met naam, totale omzet en aandeel-percentage,
uit `v_top_klanten`.

**Verkooppunt:** *"In één oogopslag zien welke klantrelaties het meest waardevol zijn
— cruciaal voor prioritering van accountmanagement."*

---

### 4. Marge per project
**Stel in:** "Wat is mijn brutomarge per project dit jaar?"

**Verwacht antwoord:** Overzicht van projecten met geoffreerd bedrag,
gefactureerd bedrag, kosten op basis van uren en bruto-margepercentage.
Projecten over budget vallen op.

**Verkooppunt:** *"Meteen zien welke projecten winstgevend zijn en welke niet —
zodat je op tijd kunt bijsturen."*

---

### 5. BTW-aangifte
**Stel in:** "Hoeveel BTW moet ik aangeven over Q1 2026?"

**Verwacht antwoord:** Af te dragen BTW (verkopen), terug te vorderen BTW (inkopen)
en het netto-saldo voor het eerste kwartaal van 2026, uit `v_btw_per_kwartaal`.

**Verkooppunt:** *"BTW-aangifte voorbereiding in één vraag — geen handmatig optellen
meer in spreadsheets."*

---

### 6. Leveranciersfacturen betalen
**Stel in:** "Welke leveranciersfacturen moet ik deze week betalen?"

**Verwacht antwoord:** Lijst van openstaande inkoopfacturen met vervaldatum binnen
7 dagen, inclusief leveranciersnaam en IBAN.

**Verkooppunt:** *"Nooit meer een leverancier te laat betalen en onnodige
aanmaningskosten oplopen."*

---

### 7. Uren per medewerker
**Stel in:** "Hoeveel uren heeft [naam medewerker] dit jaar geschreven,
en op welke projecten?"

*(Kijk eerst in de data: `SELECT naam FROM medewerkers` — kies een naam uit de lijst)*

**Verwacht antwoord:** Totaal uren en lijst van projecten voor de betreffende
medewerker in het huidige jaar.

**Verkooppunt:** *"Capaciteitsbeheer en projectbezetting in één overzicht —
handig voor planningsgesprekken."*

---

### 8. Projecten over budget
**Stel in:** "Welke projecten zijn over budget gegaan?"

**Verwacht antwoord:** Projecten waarbij de gefactureerde waarde het geoffreerde
bedrag overstijgt, gesorteerd op verschil, uit `v_marge_per_project`.

**Verkooppunt:** *"Vroeg signaleren waar het fout gaat qua budgetbewaking —
zodat je kunt bijsturen voor de volgende offerte."*

---

## Bewust lastige vragen (toon eerlijkheid van de agent)

### Schrijfactie weigeren
**Stel in:** "Verwijder alle facturen van vorig jaar."

**Verwacht:** De assistent weigert beleefd en legt uit dat hij alleen leestoegang heeft.

---

### Vraag buiten de data
**Stel in:** "Wat verdient mijn buurman?"

**Verwacht:** De assistent geeft eerlijk aan dat deze informatie niet in de database zit.

---

### Ambigue vraag
**Stel in:** "Hoe gaat het met mijn bedrijf?"

**Verwacht:** De assistent vraagt om verduidelijking of geeft een brede samenvatting
op basis van beschikbare metrics (omzet, openstaande facturen, cashflow).

---

## Tips voor het gesprek

- **Toon het SQL-paneel** na elk antwoord — dit schept vertrouwen ("de assistent
  verzint niets, hij haalt het echt op uit jouw systeem").
- **Stel een follow-upvraag** na vraag 2: "En stuur me een herinneringsmail naar die
  klanten?" — de assistent weigert terecht (alleen lezen).
- **Vergelijk snelheid**: laat de klant schatten hoelang hij er normaal over doet
  om vraag 5 (BTW-kwartaal) te beantwoorden. Dan het contrast met de 3-seconden-respons.
