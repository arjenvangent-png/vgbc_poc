"""
test_db.py
Unittest voor de veilige query-executor in app/db.py.
Test: afwijzing van non-SELECT, meerdere statements, lege queries.
Vereist geen live database-verbinding.
"""

import pytest
from db import validate_query


# ---------------------------------------------------------------------------
# Geldige SELECT-queries — mogen NIET worden geweigerd
# ---------------------------------------------------------------------------
VALID_QUERIES = [
    "SELECT 1",
    "SELECT * FROM klanten",
    "SELECT naam, omzet_excl_btw FROM v_top_klanten LIMIT 5",
    "  SELECT  COUNT(*)  FROM  facturen  WHERE  status = 'Betaald'  ",  # extra spaties
    "select klant_id from klanten",  # lowercase
    """
    SELECT f.factuurnummer, k.naam
    FROM facturen f
    JOIN klanten k ON k.klant_id = f.klant_id
    WHERE f.status = 'Achterstallig'
    """,
]

# ---------------------------------------------------------------------------
# Ongeldige queries — moeten ValueError gooien
# ---------------------------------------------------------------------------
INVALID_QUERIES = [
    ("", "Lege query"),
    ("DELETE FROM facturen", "DELETE"),
    ("DROP TABLE klanten", "DROP"),
    ("INSERT INTO klanten (naam) VALUES ('hack')", "INSERT"),
    ("UPDATE facturen SET status = 'Betaald'", "UPDATE"),
    ("SELECT 1; DROP TABLE klanten", "Meerdere statements"),
    ("CREATE TABLE pwnd (x TEXT)", "CREATE"),
    ("TRUNCATE klanten", "TRUNCATE"),
    ("ALTER TABLE klanten ADD COLUMN x TEXT", "ALTER"),
]


@pytest.mark.parametrize("sql", VALID_QUERIES)
def test_geldige_query_geaccepteerd(sql):
    """validate_query mag geen uitzondering gooien voor geldige SELECT-queries."""
    validate_query(sql)  # geen assert nodig — geen uitzondering = geslaagd


@pytest.mark.parametrize("sql,omschrijving", INVALID_QUERIES)
def test_ongeldige_query_geweigerd(sql, omschrijving):
    """validate_query moet ValueError gooien voor non-SELECT of meerdere statements."""
    with pytest.raises(ValueError, match=r".+"):
        validate_query(sql)


def test_agent_rol_kan_niet_schrijven(agent_conn):
    """
    De vgbc_agent-databasegebruiker mag geen INSERT kunnen uitvoeren —
    zelfs als validate_query zou falen (tweede vangnet).
    """
    import psycopg2
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        with agent_conn.cursor() as cur:
            cur.execute("INSERT INTO klanten (naam) VALUES ('test_hack')")
        agent_conn.commit()
    agent_conn.rollback()
