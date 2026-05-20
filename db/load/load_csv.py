"""
load_csv.py
Doel   : Laad alle CSV-bestanden uit sample-data/ in de PostgreSQL-database.
         Idempotent: TRUNCATE + INSERT in vaste volgorde (FK-veilig).
Gebruik: python db/load/load_csv.py
Vereisten: pip install psycopg2-binary python-dotenv
"""

import csv
import os
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    sys.exit("DATABASE_URL niet gevonden in .env — kopieer .env.example naar .env en vul in.")

# Pad naar sample-data (relatief aan de repo-root)
REPO_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = REPO_ROOT / "sample-data"

# Volgorde is belangrijk: eerst parent-tabellen, dan child-tabellen
LOAD_ORDER = [
    ("klanten",           "klanten.csv",            "klant_id"),
    ("leveranciers",      "leveranciers.csv",        "leverancier_id"),
    ("medewerkers",       "medewerkers.csv",         "medewerker_id"),
    ("producten_diensten","producten_diensten.csv",  "product_id"),
    ("projecten",         "projecten.csv",           "project_id"),
    ("urenregistratie",   "urenregistratie.csv",     "uur_id"),
    ("facturen",          "facturen.csv",            "factuur_id"),
    ("factuurregels",     "factuurregels.csv",       "regel_id"),
    ("betalingen",        "betalingen.csv",          "betaling_id"),
    ("inkoopfacturen",    "inkoopfacturen.csv",      "inkoop_id"),
]

NULL_VALUES = {"", "None", "NULL", "null"}


def parse_value(val: str):
    return None if val in NULL_VALUES else val


def load_table(cur, table: str, csv_path: Path, pk_col: str) -> int:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print(f"  WAARSCHUWING: {csv_path.name} is leeg, sla over.")
        return 0

    cols = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(cols))
    col_list = ", ".join(cols)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

    cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")

    data = [tuple(parse_value(row[c]) for c in cols) for row in rows]
    cur.executemany(sql, data)

    # Zet sequence op max-id zodat volgende inserts niet botsen
    cur.execute(f"""
        SELECT setval(
            pg_get_serial_sequence('{table}', '{pk_col}'),
            COALESCE(MAX({pk_col}), 1)
        ) FROM {table}
    """)

    return len(data)


def main():
    print("Laden CSV-data in PostgreSQL...\n")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    totaal = 0
    try:
        for table, filename, pk_col in LOAD_ORDER:
            csv_path = DATA_DIR / filename
            if not csv_path.exists():
                print(f"  FOUT: {csv_path} niet gevonden — draai eerst generate_data.py")
                conn.rollback()
                sys.exit(1)
            t0 = time.monotonic()
            n = load_table(cur, table, csv_path, pk_col)
            elapsed = time.monotonic() - t0
            print(f"  {n:>6} rijen geladen in '{table}' ({elapsed:.1f}s)")
            totaal += n

        conn.commit()
        print(f"\nKlaar. {totaal} rijen totaal geladen.")
    except Exception as exc:
        conn.rollback()
        print(f"\nFOUT tijdens laden: {exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
