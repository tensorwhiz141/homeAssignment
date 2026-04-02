import streamlit as st

# ── Imports ──────────────────────────────────────────────
from agent import LoanAgent
from voice import transcribe_audio, text_to_speech
from rag import is_policy_question, retrieve_context

from database import (
    generate_session_id, save_message,
    save_lead, save_handoff, get_all_leads
)

# ── Page Config ──────────────────────────────────────────
st.set_page_config(page_title="AI Loan Counselor", layout="wide")

# ── Session State Init ───────────────────────────────────
if "agent" not in st.session_state:
    st.session_state.agent = LoanAgent()

if "transcript" not in st.session_state:
    st.session_state.transcript = []

if "debug" not in st.session_state:
    st.session_state.debug = {}

if "session_id" not in st.session_state:
    st.session_state.session_id = generate_session_id()

# ── Core Function ────────────────────────────────────────
def process_message(user_message: str):
    """Message → RAG → LLM → TTS → DB → update state."""

    # Save user message
    save_message(st.session_state.session_id, "user", user_message)

    # RAG
    agent_input = user_message
    if is_policy_question(user_message):
        rag_context = retrieve_context(user_message)
        if rag_context:
            agent_input = f"[POLICY CONTEXT: {rag_context}]\n\nUser: {user_message}"

    # Add to transcript
    st.session_state.transcript.append({
        "role": "user",
        "text": user_message
    })

    # LLM
    with st.spinner("🤔 Thinking..."):
        result = st.session_state.agent.chat(agent_input)

    response_text = result["response"]
    st.session_state.debug = result

    # Save assistant message
    save_message(st.session_state.session_id, "assistant", response_text)

    # Save lead
    save_lead(
        session_id=st.session_state.session_id,
        extracted_data=result.get("extracted_data", {}),
        locked_language=result.get("locked_language", "english"),
        handoff_triggered=result.get("handoff_triggered", False)
    )

    # Save handoff
    if result.get("handoff_triggered"):
        save_handoff(
            session_id=st.session_state.session_id,
            lead_data=result.get("extracted_data", {})
        )

    # TTS
    with st.spinner("🔊 Generating voice..."):
        audio_out = text_to_speech(
            response_text,
            result.get("locked_language", "english")
        )

    # Add assistant response
    st.session_state.transcript.append({
        "role": "assistant",
        "text": response_text,
        "audio": audio_out if audio_out else None
    })

    st.rerun()

# ── UI Layout ────────────────────────────────────────────
col_chat, col_debug = st.columns([3, 1])

# ── Chat Section ─────────────────────────────────────────
with col_chat:
    st.title("🏦 AI Loan Counselor")

    # Display chat
    for msg in st.session_state.transcript:
        if msg["role"] == "user":
            st.markdown(f"**🧑 You:** {msg['text']}")
        else:
            st.markdown(f"**🤖 Assistant:** {msg['text']}")
            if msg.get("audio"):
                st.audio(msg["audio"], format="audio/wav")

    # Text input
    user_input = st.chat_input("Type your message...")
    if user_input:
        process_message(user_input)

    # ── Voice input ──
    st.markdown("#### 🎙️ Push to Talk")

    try:
        from streamlit_mic_recorder import mic_recorder

        audio_data = mic_recorder(
            start_prompt="🎙️ Click to Record",
            stop_prompt="⏹️ Click to Stop",
            key="mic"
        )

        if audio_data and audio_data.get("bytes"):
            audio_bytes = audio_data["bytes"]

            st.write(f"📊 Audio size: {len(audio_bytes)} bytes")

            if len(audio_bytes) > 1000:
                locked_lang = st.session_state.agent.locked_language or "english"

                with st.spinner("🎧 Transcribing..."):
                    transcribed = transcribe_audio(audio_bytes, locked_lang)

                if transcribed:
                    st.info(f"📝 You said: *{transcribed}*")
                    process_message(transcribed)
                else:
                    st.warning("❌ Could not transcribe. Try speaking clearly.")

            else:
                st.warning("⚠️ Audio too short. Speak longer.")

    except ImportError:
        st.warning("Run: pip install streamlit-mic-recorder")

# ── Debug Panel ──────────────────────────────────────────
with col_debug:
    st.subheader("🧪 Debug")

    if st.session_state.debug:
        st.json(st.session_state.debug)

    st.markdown("---")

    # Leads Dashboard
    if st.button("📋 View All Leads", use_container_width=True):
        leads = get_all_leads()
        if leads:
            import pandas as pd
            df = pd.DataFrame(leads)
            st.dataframe(df[[
                "session_id", "monthly_income",
                "loan_amount_requested", "eligible",
                "handoff_triggered", "created_at"
            ]])
        else:
            st.caption("No leads saved yet.")

    st.markdown("---")

    # Reset button
    if st.button("🔄 Reset Session", use_container_width=True):
        st.session_state.transcript = []
        st.session_state.debug = {}
        st.session_state.session_id = generate_session_id()
        st.rerun()