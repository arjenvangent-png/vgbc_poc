"""
db.py
Doel   : Database-verbinding en veilige query-executor voor de VGBC-agent.
         Gebruikt de read-only vgbc_agent-rol — schrijfacties zijn fysiek onmogelijk.
Gebruik: from db import run_query, get_schema_context
"""

import os
from typing import Any

import psycopg2
import psycopg2.extras
import sqlparse
from dotenv import load_dotenv

load_dotenv()

# Module-level verbinding (wordt hergebruikt binnen dezelfde Streamlit-sessie)
_connection: psycopg2.extensions.connection | None = None


def _get_connection() -> psycopg2.extensions.connection:
    global _connection
    url = os.getenv("AGENT_DATABASE_URL")
    if not url:
        raise RuntimeError("AGENT_DATABASE_URL niet ingesteld — kopieer .env.example naar .env.")
    if _connection is None or _connection.closed:
        _connection = psycopg2.connect(url)
        _connection.autocommit = True
    return _connection


# ---------------------------------------------------------------------------
# SQL-validator
# ---------------------------------------------------------------------------
def validate_query(sql: str) -> None:
    """
    Weiger alles wat geen enkelvoudig SELECT-statement is.
    Gooit ValueError bij overtreding — tweede vangnet naast de DB-rol.
    """
    stripped = sql.strip()
    if not stripped:
        raise ValueError("Lege query ontvangen.")

    # Meerdere statements blokkeren (bijv. SELECT 1; DROP TABLE ...)
    statements = [s for s in sqlparse.parse(stripped) if s.value.strip()]
    if len(statements) > 1:
        raise ValueError(
            "Meerdere SQL-statements zijn niet toegestaan. "
            "Stuur slechts één SELECT per keer."
        )

    # Eerste keyword moet SELECT zijn
    stmt_type = statements[0].get_type()
    if stmt_type != "SELECT":
        raise ValueError(
            f"Alleen SELECT-queries zijn toegestaan (gevonden type: '{stmt_type or 'onbekend'}')."
        )


# ---------------------------------------------------------------------------
# Query-uitvoering
# ---------------------------------------------------------------------------
def run_query(sql: str) -> tuple[list[dict[str, Any]], int]:
    """
    Voer een gevalideerde SELECT-query uit via de read-only agent-verbinding.
    Geeft (rijen als lijst van dicts, totaal_aantal) terug.
    Gooit ValueError (validatie) of psycopg2-fouten (SQL-fout).
    """
    validate_query(sql)
    conn = _get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
    return rows, len(rows)


# ---------------------------------------------------------------------------
# Schema-introspectie (wordt bij opstart in de system prompt geïnjecteerd)
# ---------------------------------------------------------------------------
def get_schema_context() -> str:
    """
    Haal het live schema op uit information_schema en formateer als Markdown.
    Zo blijft de agent-prompt altijd synchroon met het echte schema.
    """
    sql = """
        SELECT
            t.table_type,
            t.table_name,
            c.column_name,
            c.data_type,
            c.is_nullable,
            CASE WHEN pk.column_name IS NOT NULL THEN 'PK' ELSE '' END        AS pk_flag,
            COALESCE(
                'FK -> ' || fk.foreign_table || '.' || fk.foreign_col, ''
            )                                                                  AS fk_flag
        FROM information_schema.tables t
        JOIN information_schema.columns c
            ON c.table_name = t.table_name
           AND c.table_schema = t.table_schema
        LEFT JOIN (
            SELECT kcu.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON kcu.constraint_name = tc.constraint_name
               AND kcu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
        ) pk ON pk.table_name = c.table_name AND pk.column_name = c.column_name
        LEFT JOIN (
            SELECT
                kcu.table_name,
                kcu.column_name,
                ccu.table_name  AS foreign_table,
                ccu.column_name AS foreign_col
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON kcu.constraint_name = tc.constraint_name
               AND kcu.table_schema = tc.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
               AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
        ) fk ON fk.table_name = c.table_name AND fk.column_name = c.column_name
        WHERE t.table_schema = 'public'
          AND t.table_type IN ('BASE TABLE', 'VIEW')
        ORDER BY t.table_type DESC, t.table_name, c.ordinal_position
    """
    try:
        rows, _ = run_query(sql)
    except Exception as exc:
        return f"_(Schema kon niet worden opgehaald: {exc})_"

    lines: list[str] = []
    current_type = None
    current_table = None

    for row in rows:
        tbl_type = "Tabellen" if row["table_type"] == "BASE TABLE" else "Views"
        tbl_name = row["table_name"]

        if tbl_type != current_type:
            current_type = tbl_type
            lines.append(f"\n#### {tbl_type}")

        if tbl_name != current_table:
            current_table = tbl_name
            lines.append(f"\n**{tbl_name}**")

        nullable = "" if row["is_nullable"] == "YES" else " NOT NULL"
        flags = " ".join(filter(None, [row["pk_flag"], row["fk_flag"]]))
        col_line = f"  - `{row['column_name']}` {row['data_type']}{nullable}"
        if flags:
            col_line += f"  _{flags}_"
        lines.append(col_line)

    return "\n".join(lines)
