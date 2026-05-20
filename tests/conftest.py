"""
conftest.py — gedeelde pytest-fixtures voor de VGBC POC-testsuite.
"""

import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
import pytest
from dotenv import load_dotenv

# Voeg app-map toe zodat db.py gevonden wordt
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

load_dotenv(Path(__file__).parent.parent / ".env")


@pytest.fixture(scope="session")
def db_conn():
    """Verbinding met schrijfrechten (voor rij-count verificatie)."""
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL niet ingesteld — sla DB-tests over.")
    conn = psycopg2.connect(url)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def agent_conn():
    """Read-only verbinding via vgbc_agent-rol."""
    url = os.getenv("AGENT_DATABASE_URL")
    if not url:
        pytest.skip("AGENT_DATABASE_URL niet ingesteld — sla agent-tests over.")
    conn = psycopg2.connect(url)
    conn.autocommit = True
    yield conn
    conn.close()
