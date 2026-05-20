"""
main.py
Doel   : Streamlit-chatbot voor de VGBC MKB-bedrijfsassistent.
         Start met: streamlit run app/main.py
"""

import os
import sys
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Voeg app-map toe aan het pad zodat db en agent gevonden worden
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from agent import MODEL, chat
from db import get_schema_context

# ---------------------------------------------------------------------------
# Paginaconfiguratie
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="VGBC Bedrijfsassistent",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Schema éénmaal ophalen per sessie (gecached)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Databaseschema ophalen...")
def load_schema() -> str:
    return get_schema_context()


# ---------------------------------------------------------------------------
# Sessiestatus initialiseren
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []        # gespreksgeschiedenis voor de API
if "display_messages" not in st.session_state:
    st.session_state.display_messages = []  # berichten inclusief SQL-metadata

# ---------------------------------------------------------------------------
# Zijbalk
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image("https://via.placeholder.com/200x60?text=VGBC", width=200)
    st.markdown("## ⚙️ Instellingen")

    model_choice = st.selectbox(
        "LLM-model",
        options=["claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
        index=0,
        help="Sonnet = hogere kwaliteit · Haiku = sneller & goedkoper",
    )
    os.environ["LLM_MODEL"] = model_choice

    st.divider()
    st.markdown("### 💡 Voorbeeldvragen")
    voorbeelden = [
        "Wat was mijn omzet in maart 2026?",
        "Welke klanten hebben facturen >30 dagen open?",
        "Wie zijn mijn top 5 klanten qua omzet?",
        "Wat is mijn brutomarge per project dit jaar?",
        "Hoeveel BTW moet ik aangeven over Q1 2026?",
        "Welke leveranciersfacturen moet ik deze week betalen?",
        "Welke projecten zijn over budget gegaan?",
    ]
    for vb in voorbeelden:
        if st.button(vb, use_container_width=True, key=f"vb_{vb[:20]}"):
            st.session_state["prefill"] = vb

    st.divider()
    if st.button("🗑️ Gesprek wissen", use_container_width=True):
        st.session_state.messages = []
        st.session_state.display_messages = []
        st.rerun()

    st.markdown("---")
    st.caption(f"Model: `{model_choice}`")
    st.caption("Alleen leestoegang · Geen secrets in code")

# ---------------------------------------------------------------------------
# Hoofdpanel — koptekst
# ---------------------------------------------------------------------------
st.title("📊 VGBC Bedrijfsassistent")
st.caption(
    "Stel vragen over je administratie in gewone taal. "
    "De assistent zoekt de data op en legt uit wat hij vindt."
)

# Schema laden (gecached)
schema_context = load_schema()

# ---------------------------------------------------------------------------
# Gespreksgeschiedenis weergeven
# ---------------------------------------------------------------------------
for msg in st.session_state.display_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Transparantie-paneel onder elk antwoord van de assistent
        if msg["role"] == "assistant" and msg.get("sql"):
            with st.expander("🔍 Uitgevoerde SQL & resultaat", expanded=False):
                st.code(msg["sql"], language="sql")
                rows = msg.get("rows")
                if rows is not None:
                    st.caption(f"↳ {rows} rij{'en' if rows != 1 else ''} gevonden")

# ---------------------------------------------------------------------------
# Invoerveld
# ---------------------------------------------------------------------------
prefill = st.session_state.pop("prefill", "")
user_input = st.chat_input(
    "Stel een vraag over je bedrijf...",
    key="chat_input",
) or prefill

if user_input:
    # Gebruikersbericht tonen
    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.display_messages.append(
        {"role": "user", "content": user_input}
    )
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    # Assistent antwoord
    with st.chat_message("assistant"):
        with st.spinner("Even nadenken..."):
            t0 = time.monotonic()
            result = chat(
                messages=st.session_state.messages,
                schema_context=schema_context,
                user_question=user_input,
            )
            elapsed = time.monotonic() - t0

        answer = result["text"]
        sql = result.get("sql")
        rows = result.get("rows")

        st.markdown(answer)

        # Transparantie-paneel direct onder het antwoord
        if sql:
            with st.expander("🔍 Uitgevoerde SQL & resultaat", expanded=True):
                st.code(sql, language="sql")
                if rows is not None:
                    st.caption(f"↳ {rows} rij{'en' if rows != 1 else ''} gevonden · {elapsed:.1f}s")

        if result.get("error"):
            st.warning(f"⚠️ {result['error']}")

    # Gesprek bijwerken
    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
    st.session_state.display_messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sql": sql,
            "rows": rows,
        }
    )
