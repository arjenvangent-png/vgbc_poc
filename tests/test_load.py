"""
test_load.py
Verificeert dat elke tabel het verwachte minimum aantal rijen bevat na het laden.
"""

import pytest

# Minimale verwachte aantallen (iets lager dan gegenereerd voor robuustheid)
MIN_ROW_COUNTS = {
    "klanten":            80,
    "leveranciers":       20,
    "medewerkers":         8,
    "producten_diensten": 30,
    "projecten":         150,
    "urenregistratie":  4500,
    "facturen":         2400,
    "factuurregels":    8000,
    "betalingen":       1500,
    "inkoopfacturen":   1100,
}


def count_rows(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
        return cur.fetchone()[0]


@pytest.mark.parametrize("tabel,minimum", MIN_ROW_COUNTS.items())
def test_rij_aantallen(db_conn, tabel, minimum):
    aantal = count_rows(db_conn, tabel)
    assert aantal >= minimum, (
        f"Tabel '{tabel}' heeft {aantal} rijen, verwacht minimaal {minimum}. "
        "Draai 'make load' opnieuw."
    )


def test_dubieuze_debiteuren_aanwezig(db_conn):
    """Klant-IDs 5, 12 en 23 moeten gemarkeerd zijn als dubieus."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM klanten WHERE is_dubieus = TRUE AND klant_id IN (5, 12, 23)"
        )
        assert cur.fetchone()[0] == 3, "Drie dubieuze debiteuren (IDs 5/12/23) verwacht."


def test_creditfacturen_aanwezig(db_conn):
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM facturen WHERE is_creditfactuur = TRUE")
        assert cur.fetchone()[0] > 0, "Er zouden creditfacturen aanwezig moeten zijn."


def test_openstaande_facturen_aanwezig(db_conn):
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM facturen WHERE status IN ('Openstaand', 'Achterstallig')")
        assert cur.fetchone()[0] > 0, "Er zouden openstaande facturen moeten zijn."
