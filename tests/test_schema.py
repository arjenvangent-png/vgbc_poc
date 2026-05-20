"""
test_schema.py
Verificeert dat alle verwachte tabellen en views in de database aanwezig zijn.
"""

import pytest

EXPECTED_TABLES = [
    "klanten",
    "leveranciers",
    "medewerkers",
    "producten_diensten",
    "projecten",
    "urenregistratie",
    "facturen",
    "factuurregels",
    "betalingen",
    "inkoopfacturen",
]

EXPECTED_VIEWS = [
    "v_omzet_per_maand",
    "v_openstaande_debiteuren",
    "v_marge_per_project",
    "v_top_klanten",
    "v_cashflow_per_week",
    "v_btw_per_kwartaal",
    "v_openstaande_inkoopfacturen",
]


def fetch_names(conn, table_type: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = %s",
            (table_type,),
        )
        return {row[0] for row in cur.fetchall()}


@pytest.mark.parametrize("tabel", EXPECTED_TABLES)
def test_tabel_bestaat(db_conn, tabel):
    aanwezige = fetch_names(db_conn, "BASE TABLE")
    assert tabel in aanwezige, f"Tabel '{tabel}' ontbreekt in de database."


@pytest.mark.parametrize("view", EXPECTED_VIEWS)
def test_view_bestaat(db_conn, view):
    aanwezige = fetch_names(db_conn, "VIEW")
    assert view in aanwezige, f"View '{view}' ontbreekt in de database."


def test_views_bevraagbaar(db_conn):
    """Elke view moet zonder fout een SELECT * LIMIT 1 overleven."""
    for view in EXPECTED_VIEWS:
        with db_conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {view} LIMIT 1")  # noqa: S608
