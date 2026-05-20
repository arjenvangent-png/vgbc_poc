"""
agent.py
Doel   : LLM-agent-loop met tool-use (function calling) via de Anthropic API.
         De agent roept run_sql aan, logt elke query, en herprobeert bij een
         SQL-fout maximaal één keer met de foutmelding als extra context.
Gebruik: from agent import chat
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv

from db import get_schema_context, run_query, validate_query

load_dotenv()

# ---------------------------------------------------------------------------
# Configuratie
# ---------------------------------------------------------------------------
LOG_FILE = Path(__file__).parent / "logs" / "queries.jsonl"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
MAX_TOOL_ROUNDS = 4   # max tool-use rondes per gebruikersbericht (voorkomt loops)
MAX_ROWS_IN_CONTEXT = 200  # max rijen die we naar het model sturen

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key.startswith("sk-ant-vervang"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY niet ingesteld — vul je sleutel in in .env."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Tool-definitie voor Claude
# ---------------------------------------------------------------------------
TOOLS: list[dict] = [
    {
        "name": "run_sql",
        "description": (
            "Voer een PostgreSQL SELECT-query uit op de VGBC-bedrijfsdatabase. "
            "Gebruik dit voor het ophalen van gegevens over klanten, facturen, projecten, "
            "medewerkers, omzet, debiteuren, cashflow en BTW. "
            "Schrijfacties (INSERT/UPDATE/DELETE/DROP) worden geweigerd."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Een geldige PostgreSQL SELECT-query. "
                        "Gebruik views (v_*) waar mogelijk."
                    ),
                }
            },
            "required": ["query"],
        },
    }
]


# ---------------------------------------------------------------------------
# Query-log
# ---------------------------------------------------------------------------
def _log_query(
    sql: str,
    rows: int,
    latency_s: float,
    success: bool,
    user_question: str = "",
    error: str = "",
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": user_question,
        "sql": sql,
        "rows": rows,
        "latency_s": round(latency_s, 3),
        "success": success,
    }
    if error:
        entry["error"] = error
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


# ---------------------------------------------------------------------------
# Tool-uitvoering
# ---------------------------------------------------------------------------
def _execute_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    user_question: str = "",
) -> tuple[str, str | None, int | None]:
    """
    Voer de tool uit en geef (resultaat_tekst, sql, rij_aantal) terug.
    Bij een fout wordt de foutmelding als tekst teruggegeven zodat Claude
    één herpoging kan doen met gecorrigeerde SQL.
    """
    if tool_name != "run_sql":
        return f"Onbekende tool: '{tool_name}'.", None, None

    sql = tool_input.get("query", "").strip()
    t0 = time.monotonic()

    try:
        validate_query(sql)
        rows, count = run_query(sql)
        latency = time.monotonic() - t0

        _log_query(sql, count, latency, success=True, user_question=user_question)

        # Beperk het aantal rijen dat we naar het model sturen
        result_rows = rows[:MAX_ROWS_IN_CONTEXT]
        result_text = json.dumps(result_rows, ensure_ascii=False, default=str)
        if count > MAX_ROWS_IN_CONTEXT:
            result_text += (
                f"\n\n[Opmerking: {count} rijen totaal gevonden, "
                f"eerste {MAX_ROWS_IN_CONTEXT} getoond.]"
            )
        return result_text, sql, count

    except Exception as exc:
        latency = time.monotonic() - t0
        error_msg = str(exc)
        _log_query(sql, 0, latency, success=False, user_question=user_question, error=error_msg)
        return f"SQL-FOUT: {error_msg}", sql, 0


# ---------------------------------------------------------------------------
# Systeem-prompt laden
# ---------------------------------------------------------------------------
def load_system_prompt(schema_context: str) -> str:
    prompt_path = Path(__file__).parent / "prompts" / "system.md"
    base = prompt_path.read_text(encoding="utf-8")
    return base.replace("{{SCHEMA}}", schema_context)


# ---------------------------------------------------------------------------
# Hoofd-agent-loop
# ---------------------------------------------------------------------------
def chat(
    messages: list[dict],
    schema_context: str,
    user_question: str = "",
) -> dict[str, Any]:
    """
    Stuur de gespreksgeschiedenis naar de agent en geef een antwoord-dict terug:
    {
        "text":  str,           # het geformuleerde antwoord
        "sql":   str | None,    # de laatste uitgevoerde SQL (voor transparantie-paneel)
        "rows":  int | None,    # aantal teruggekeerde rijen
        "error": str | None,    # eventuele foutmelding
    }
    """
    system_prompt = load_system_prompt(schema_context)
    history = list(messages)
    last_sql: str | None = None
    last_rows: int | None = None

    for _ in range(MAX_TOOL_ROUNDS):
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system_prompt,
            tools=TOOLS,
            messages=history,
        )

        if response.stop_reason == "end_turn":
            # Model is klaar — haal antwoordtekst op
            answer = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            return {"text": answer, "sql": last_sql, "rows": last_rows, "error": None}

        if response.stop_reason == "tool_use":
            # Model wil een tool aanroepen
            history.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result_text, sql, rows = _execute_tool(
                    block.name, block.input, user_question=user_question
                )
                if sql is not None:
                    last_sql = sql
                if rows is not None:
                    last_rows = rows
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    }
                )

            history.append({"role": "user", "content": tool_results})
            # Volgende iteratie: Claude formuleert antwoord of doet nog een tool-call
            continue

        # Onverwachte stop_reason
        break

    # Maximaal aantal rondes bereikt of onverwachte toestand
    return {
        "text": (
            "Het is me helaas niet gelukt een volledig antwoord te formuleren. "
            "Probeer de vraag anders of specifieker te stellen."
        ),
        "sql": last_sql,
        "rows": last_rows,
        "error": "Maximaal aantal tool-rondes bereikt.",
    }
