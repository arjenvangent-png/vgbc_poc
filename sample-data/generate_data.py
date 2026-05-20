"""
Genereert synthetische MKB-testdata voor de VGBC POC.
Produceert CSV-bestanden in dezelfde map als dit script.
Gebruik: python generate_data.py
Vereisten: pip install faker
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path
from faker import Faker

fake = Faker("nl_NL")
random.seed(42)
Faker.seed(42)

OUT = Path(__file__).parent
START_DATE = date(2023, 1, 1)
END_DATE = date(2026, 5, 20)
TODAY = END_DATE

BTW_TARIEVEN = [0.09, 0.21]
BETAALMETHODEN = ["iDEAL", "Overboeking", "Automatische incasso", "PIN", "Contant"]
PROJECT_STATUSSEN = ["Offerte", "Lopend", "Afgerond", "Geannuleerd"]
FACTUUR_STATUSSEN = ["Betaald", "Openstaand", "Achterstallig", "Gecrediteerd"]
INKOOP_STATUSSEN = ["Betaald", "Openstaand", "Achterstallig"]
EENHEDEN = ["uur", "dag", "stuk", "m²", "m", "kg", "liter", "set"]

ROLLEN = [
    "Projectleider", "Uitvoerder", "Assistent", "Boekhouder",
    "Planner", "Kwaliteitscontroleur", "Voorman", "Directeur",
]

DIENSTEN = [
    ("Advies en consultancy", "uur", 95.00, 0.21),
    ("Projectbegeleiding", "uur", 85.00, 0.21),
    ("Uitvoering schilderwerk buiten", "m²", 18.50, 0.21),
    ("Uitvoering schilderwerk binnen", "m²", 14.00, 0.21),
    ("Behangen", "m²", 22.00, 0.21),
    ("Stucwerk", "m²", 35.00, 0.21),
    ("Houtrot herstel", "uur", 75.00, 0.21),
    ("Schuurwerk en voorbereiding", "uur", 55.00, 0.21),
    ("Gevelreiniging", "m²", 8.00, 0.21),
    ("Dakgoot behandeling", "m", 12.00, 0.21),
    ("Grondverf aanbrengen", "m²", 6.50, 0.21),
    ("Lakken kozijnen", "stuk", 45.00, 0.21),
    ("Kleuradvies", "uur", 65.00, 0.21),
    ("Snoeien en onderhoud", "uur", 60.00, 0.21),
    ("Tuinaanleg", "m²", 25.00, 0.21),
    ("Bestrating", "m²", 40.00, 0.21),
    ("Autodetailing", "stuk", 120.00, 0.21),
    ("APK-keuring begeleiding", "stuk", 35.00, 0.21),
    ("Kleine reparaties", "uur", 65.00, 0.21),
    ("Materiaal verf (liter)", "liter", 8.50, 0.21),
    ("Materiaal grondverf (liter)", "liter", 6.00, 0.21),
    ("Schuurpapier (set)", "set", 12.00, 0.21),
    ("Kwasten en rollers (set)", "set", 18.00, 0.21),
    ("Afplakfolie (m²)", "m²", 2.50, 0.21),
    ("Houtbeschermingsproduct (liter)", "liter", 14.00, 0.21),
    ("Kitten en afdichtmiddel (stuk)", "stuk", 9.00, 0.21),
    ("Steiger huur (dag)", "dag", 85.00, 0.21),
    ("Hoogwerker huur (dag)", "dag", 180.00, 0.21),
    ("Cursus veiligheid op hoogte", "stuk", 250.00, 0.21),
    ("Omzetbelasting correctie", "stuk", 0.00, 0.09),
]

# Dubieuze debiteuren: klant-IDs 5, 12, 23 krijgen structureel te late betalingen
DUBIEUZE_DEBITEUREN = {5, 12, 23}


def rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def write_csv(filename: str, rows: list[dict], fieldnames: list[str]) -> None:
    path = OUT / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {len(rows):>6} rijen -> {filename}")


# ---------------------------------------------------------------------------
# 1. Klanten
# ---------------------------------------------------------------------------
def gen_klanten(n=80) -> list[dict]:
    rows = []
    bedrijfsvormen = ["B.V.", "V.O.F.", "Eenmanszaak", "N.V.", "Stichting", ""]
    betaaltermijnen = [14, 30, 45, 60]
    for i in range(1, n + 1):
        is_bedrijf = random.random() < 0.65
        if is_bedrijf:
            naam = fake.company() + " " + random.choice(bedrijfsvormen)
            btw_nr = f"NL{fake.numerify('########')}B{fake.numerify('##')}"
        else:
            naam = fake.name()
            btw_nr = ""
        rows.append({
            "klant_id": i,
            "naam": naam,
            "is_bedrijf": is_bedrijf,
            "straat": fake.street_address(),
            "postcode": fake.postcode(),
            "plaats": fake.city(),
            "email": fake.email(),
            "telefoon": fake.phone_number(),
            "btw_nummer": btw_nr,
            "betaaltermijn_dagen": random.choice(betaaltermijnen),
            "is_dubieus": i in DUBIEUZE_DEBITEUREN,
        })
    return rows


# ---------------------------------------------------------------------------
# 2. Leveranciers
# ---------------------------------------------------------------------------
def gen_leveranciers(n=20) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "leverancier_id": i,
            "naam": fake.company() + " " + random.choice(["B.V.", "V.O.F.", "N.V.", ""]),
            "straat": fake.street_address(),
            "postcode": fake.postcode(),
            "plaats": fake.city(),
            "email": fake.email(),
            "telefoon": fake.phone_number(),
            "iban": fake.iban(),
            "btw_nummer": f"NL{fake.numerify('########')}B{fake.numerify('##')}",
        })
    return rows


# ---------------------------------------------------------------------------
# 3. Medewerkers
# ---------------------------------------------------------------------------
def gen_medewerkers(n=8) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "medewerker_id": i,
            "naam": fake.name(),
            "rol": ROLLEN[i - 1],
            "email": fake.email(),
            "uurtarief": round(random.uniform(45, 95), 2),
            "in_dienst_datum": str(rand_date(date(2020, 1, 1), date(2023, 6, 1))),
        })
    return rows


# ---------------------------------------------------------------------------
# 4. Producten / diensten
# ---------------------------------------------------------------------------
def gen_producten() -> list[dict]:
    rows = []
    for i, (omschrijving, eenheid, prijs, btw) in enumerate(DIENSTEN, 1):
        rows.append({
            "product_id": i,
            "omschrijving": omschrijving,
            "eenheid": eenheid,
            "verkoopprijs": prijs,
            "btw_tarief": btw,
            "actief": True,
        })
    return rows


# ---------------------------------------------------------------------------
# 5. Projecten
# ---------------------------------------------------------------------------
def gen_projecten(klanten: list[dict], n=150) -> list[dict]:
    rows = []
    klant_ids = [k["klant_id"] for k in klanten]
    for i in range(1, n + 1):
        start = rand_date(START_DATE, date(2026, 2, 1))
        duur = random.randint(5, 180)
        eind = start + timedelta(days=duur)
        geoffreerd = round(random.uniform(500, 35000), 2)
        status = random.choices(
            PROJECT_STATUSSEN, weights=[0.05, 0.20, 0.70, 0.05]
        )[0]
        rows.append({
            "project_id": i,
            "naam": f"Project {fake.bs().title()[:40]}",
            "klant_id": random.choice(klant_ids),
            "status": status,
            "startdatum": str(start),
            "einddatum": str(eind),
            "geoffreerd_bedrag": geoffreerd,
            "omschrijving": fake.sentence(nb_words=8),
        })
    return rows


# ---------------------------------------------------------------------------
# 6. Urenregistratie
# ---------------------------------------------------------------------------
def gen_uren(projecten: list[dict], medewerkers: list[dict], n=5000) -> list[dict]:
    rows = []
    proj_ids = [p["project_id"] for p in projecten if p["status"] in ("Lopend", "Afgerond")]
    med_ids = [m["medewerker_id"] for m in medewerkers]
    for i in range(1, n + 1):
        datum = rand_date(START_DATE, TODAY)
        uren = round(random.choice([1, 2, 3, 4, 6, 7, 8]) + random.choice([0, 0.5]), 1)
        rows.append({
            "uur_id": i,
            "project_id": random.choice(proj_ids),
            "medewerker_id": random.choice(med_ids),
            "datum": str(datum),
            "uren": uren,
            "omschrijving": fake.sentence(nb_words=5),
        })
    return rows


# ---------------------------------------------------------------------------
# 7. Facturen + factuurregels + betalingen
# ---------------------------------------------------------------------------
def gen_facturen_en_regels(
    klanten: list[dict],
    producten: list[dict],
    projecten: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    facturen = []
    regels = []
    betalingen = []
    regel_id = 1
    betaling_id = 1
    klant_ids = [k["klant_id"] for k in klanten]
    prod_ids = [p["product_id"] for p in producten]
    proj_map = {p["project_id"]: p for p in projecten}
    klant_termijn = {k["klant_id"]: k["betaaltermijn_dagen"] for k in klanten}

    credit_count = 0
    for factuur_id in range(1, 2501):
        klant_id = random.choice(klant_ids)
        is_dubieus = klant_id in DUBIEUZE_DEBITEUREN
        datum = rand_date(START_DATE, date(2026, 4, 30))
        termijn = klant_termijn.get(klant_id, 30)
        vervaldatum = datum + timedelta(days=termijn)

        # ~3% is een creditfactuur
        is_credit = credit_count < 75 and random.random() < 0.03
        if is_credit:
            credit_count += 1

        # Project koppelen (niet altijd)
        project_id = ""
        if random.random() < 0.75:
            project_id = random.choice(list(proj_map.keys()))

        # Factuurregels genereren
        n_regels = random.randint(1, 6)
        totaal_excl = 0.0
        totaal_btw = 0.0
        for _ in range(n_regels):
            prod = random.choice(producten)
            aantal = round(random.uniform(1, 20), 1)
            eenheidsprijs = prod["verkoopprijs"]
            btw_tarief = prod["btw_tarief"]
            regel_excl = round(aantal * eenheidsprijs, 2)
            if is_credit:
                regel_excl = -abs(regel_excl)
            regel_btw = round(regel_excl * btw_tarief, 2)
            totaal_excl += regel_excl
            totaal_btw += regel_btw
            regels.append({
                "regel_id": regel_id,
                "factuur_id": factuur_id,
                "product_id": prod["product_id"],
                "omschrijving": prod["omschrijving"],
                "aantal": aantal,
                "eenheidsprijs": eenheidsprijs,
                "btw_tarief": btw_tarief,
                "bedrag_excl_btw": regel_excl,
                "bedrag_btw": regel_btw,
            })
            regel_id += 1

        totaal_excl = round(totaal_excl, 2)
        totaal_incl = round(totaal_excl + totaal_btw, 2)

        # Bepaal status
        # Realistisch model: hoe ouder de factuur, hoe groter de kans dat hij
        # inmiddels betaald is — ook als hij ooit te laat was.
        dagen_open = (TODAY - vervaldatum).days
        if is_credit:
            status = "Gecrediteerd"
        elif is_dubieus:
            if vervaldatum < TODAY:
                # Dubieuze klanten: 55% kans nog steeds achterstallig
                status = random.choices(["Achterstallig", "Betaald"], weights=[0.55, 0.45])[0]
            else:
                status = random.choices(["Openstaand", "Betaald"], weights=[0.7, 0.3])[0]
        elif vervaldatum > TODAY:
            # Nog niet vervallen: merendeels openstaand, sommigen al vooruitbetaald
            status = random.choices(["Openstaand", "Betaald"], weights=[0.55, 0.45])[0]
        elif dagen_open <= 14:
            # Net vervallen: kans op openstaand/achterstallig is nog reëel
            status = random.choices(["Betaald", "Openstaand", "Achterstallig"], weights=[0.60, 0.28, 0.12])[0]
        elif dagen_open <= 30:
            status = random.choices(["Betaald", "Openstaand", "Achterstallig"], weights=[0.70, 0.18, 0.12])[0]
        elif dagen_open <= 60:
            # 1-2 maanden open: meeste zijn betaald, een deel achterstallig
            status = random.choices(["Betaald", "Achterstallig"], weights=[0.75, 0.25])[0]
        elif dagen_open <= 90:
            status = random.choices(["Betaald", "Achterstallig"], weights=[0.80, 0.20])[0]
        else:
            # Meer dan 3 maanden oud: bijna allemaal betaald
            status = random.choices(["Betaald", "Achterstallig"], weights=[0.88, 0.12])[0]

        facturen.append({
            "factuur_id": factuur_id,
            "factuurnummer": f"F{datum.year}-{factuur_id:05d}",
            "klant_id": klant_id,
            "project_id": project_id,
            "datum": str(datum),
            "vervaldatum": str(vervaldatum),
            "bedrag_excl_btw": totaal_excl,
            "bedrag_btw": round(totaal_btw, 2),
            "bedrag_incl_btw": totaal_incl,
            "status": status,
            "is_creditfactuur": is_credit,
        })

        # Betaling aanmaken als status Betaald en bedrag > 0
        if status == "Betaald" and abs(totaal_incl) > 0.01:
            betaaldatum = vervaldatum + timedelta(days=random.randint(-5, 15))
            if betaaldatum > TODAY:
                betaaldatum = TODAY
            betalingen.append({
                "betaling_id": betaling_id,
                "factuur_id": factuur_id,
                "datum": str(betaaldatum),
                "bedrag": abs(totaal_incl),
                "methode": random.choice(BETAALMETHODEN),
            })
            betaling_id += 1

    return facturen, regels, betalingen


# ---------------------------------------------------------------------------
# 8. Inkoopfacturen
# ---------------------------------------------------------------------------
def gen_inkoopfacturen(leveranciers: list[dict], n=1200) -> list[dict]:
    rows = []
    lev_ids = [l["leverancier_id"] for l in leveranciers]
    for i in range(1, n + 1):
        datum = rand_date(START_DATE, date(2026, 4, 30))
        vervaldatum = datum + timedelta(days=random.choice([14, 30, 45]))
        dagen_open = (TODAY - vervaldatum).days
        bedrag_excl = round(random.uniform(50, 8000), 2)
        btw_tarief = random.choice(BTW_TARIEVEN)
        bedrag_btw = round(bedrag_excl * btw_tarief, 2)

        if vervaldatum > TODAY:
            status = random.choices(["Openstaand", "Betaald"], weights=[0.4, 0.6])[0]
        elif dagen_open <= 14:
            status = random.choices(["Betaald", "Openstaand", "Achterstallig"], weights=[0.6, 0.25, 0.15])[0]
        else:
            status = random.choices(["Betaald", "Achterstallig"], weights=[0.65, 0.35])[0]

        rows.append({
            "inkoop_id": i,
            "inkoopnummer": f"INK{datum.year}-{i:05d}",
            "leverancier_id": random.choice(lev_ids),
            "datum": str(datum),
            "vervaldatum": str(vervaldatum),
            "omschrijving": fake.sentence(nb_words=6),
            "bedrag_excl_btw": bedrag_excl,
            "btw_tarief": btw_tarief,
            "bedrag_btw": bedrag_btw,
            "bedrag_incl_btw": round(bedrag_excl + bedrag_btw, 2),
            "status": status,
        })
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Genereren synthetische MKB-testdata...\n")

    klanten = gen_klanten(80)
    leveranciers = gen_leveranciers(20)
    medewerkers = gen_medewerkers(8)
    producten = gen_producten()
    projecten = gen_projecten(klanten, 150)
    uren = gen_uren(projecten, medewerkers, 5000)
    facturen, regels, betalingen = gen_facturen_en_regels(klanten, producten, projecten)
    inkoopfacturen = gen_inkoopfacturen(leveranciers, 1200)

    write_csv("klanten.csv", klanten, list(klanten[0].keys()))
    write_csv("leveranciers.csv", leveranciers, list(leveranciers[0].keys()))
    write_csv("medewerkers.csv", medewerkers, list(medewerkers[0].keys()))
    write_csv("producten_diensten.csv", producten, list(producten[0].keys()))
    write_csv("projecten.csv", projecten, list(projecten[0].keys()))
    write_csv("urenregistratie.csv", uren, list(uren[0].keys()))
    write_csv("facturen.csv", facturen, list(facturen[0].keys()))
    write_csv("factuurregels.csv", regels, list(regels[0].keys()))
    write_csv("betalingen.csv", betalingen, list(betalingen[0].keys()))
    write_csv("inkoopfacturen.csv", inkoopfacturen, list(inkoopfacturen[0].keys()))

    print("\nKlaar. Alle CSV's staan in:", OUT)
    print(f"\nEdge cases ingebouwd:")
    print(f"  Dubieuze debiteuren : klant_id {sorted(DUBIEUZE_DEBITEUREN)}")
    credit_count = sum(1 for f in facturen if f["is_creditfactuur"])
    print(f"  Creditfacturen      : {credit_count}")
    achter_30 = sum(1 for f in facturen if f["status"] == "Achterstallig"
                    and (TODAY - date.fromisoformat(f["vervaldatum"])).days > 30)
    print(f"  Facturen >30d open  : {achter_30}")


if __name__ == "__main__":
    main()
