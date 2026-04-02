# app.py
import streamlit as st
from agent import LoanCounselorAgent
from voice import transcribe_audio, text_to_speech
from rag import retrieve_context, is_policy_question
from database import (
    generate_session_id, save_message,
    save_lead, save_handoff, get_all_leads
)

# ── Page config ──────────────────────────────────────────
st.set_page_config(
    page_title="HomeFirst Loan Counselor",
    page_icon="🏠",
    layout="wide"
)

# ── Session state init ────────────────────────────────────
if "agent" not in st.session_state:
    st.session_state.agent = LoanCounselorAgent()

if "transcript" not in st.session_state:
    st.session_state.transcript = []

if "debug" not in st.session_state:
    st.session_state.debug = {}

if "session_id" not in st.session_state:
    st.session_state.session_id = generate_session_id()


# ── Core pipeline ─────────────────────────────────────────
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

    # Add response
    st.session_state.transcript.append({
        "role": "assistant",
        "text": response_text,
        "audio": audio_out if audio_out else None
    })

    st.rerun()


# ── UI ───────────────────────────────────────────────────
st.title("🏠 HomeFirst Vernacular Loan Counselor")
st.caption("Speak or type in English, Hindi, Marathi, or Tamil")

# Handoff alert
if st.session_state.debug.get("handoff_triggered"):
    st.error("🚨 [HANDOFF TRIGGERED: Routing to Human RM]")

col_chat, col_debug = st.columns([2, 1])

# ── CHAT ─────────────────────────────────────────────────
with col_chat:
    st.subheader("💬 Conversation")

    for turn in st.session_state.transcript:
        if turn["role"] == "user":
            st.chat_message("user").write(turn["text"])
        else:
            with st.chat_message("assistant"):
                st.write(turn["text"])
                if turn.get("audio"):
                    st.audio(turn["audio"], format="audio/wav")

    st.divider()

    # ── Voice input ──
    st.markdown("#### 🎙️ Push to Talk")
    try:
        from streamlit_mic_recorder import mic_recorder
        from voice import convert_to_wav

        audio_data = mic_recorder(
            start_prompt="🎙️ Click to Record",
            stop_prompt="⏹️ Click to Stop",
            key="mic"
        )

        if audio_data and audio_data.get("bytes"):
            audio_bytes = audio_data["bytes"]

            # Debug
            st.write(f"📊 Audio size: {len(audio_bytes)} bytes")

            if len(audio_bytes) > 1000:
                locked_lang = st.session_state.agent.locked_language or "english"

                # Convert audio
                with st.spinner("🔄 Converting audio..."):
                    wav_bytes = convert_to_wav(audio_bytes)

                st.write(f"📊 WAV size: {len(wav_bytes)} bytes")

                # Transcribe
                with st.spinner("🎧 Transcribing..."):
                    transcribed = transcribe_audio(wav_bytes, locked_lang)

                if transcribed:
                    st.info(f"📝 You said: *{transcribed}*")
                    process_message(transcribed)
                else:
                    st.warning("Could not transcribe. Please speak clearly and try again.")
            else:
                st.warning("Audio too short. Please hold and speak longer.")

    except ImportError:
        st.warning("Run: pip install streamlit-mic-recorder pydub")

    # ── Text input ──
    st.markdown("#### ⌨️ Or Type Your Message")
    user_text = st.chat_input("Type here in any language...")
    if user_text:
        process_message(user_text)


# ── DEBUG PANEL ──────────────────────────────────────────
with col_debug:
    st.subheader("🔍 LLM Debug Panel")

    d = st.session_state.debug

    if d:
        st.metric("🌐 Locked Language", (d.get("locked_language") or "Detecting").upper())
        st.metric("🔧 Tool Called", "✅ Yes" if d.get("tool_called") else "❌ No")
        st.metric("👤 Human Handoff", "🚨 Triggered" if d.get("handoff_triggered") else "⏳ Pending")

        st.markdown("---")
        st.markdown("**📊 Extracted JSON:**")

        extracted = d.get("extracted_data", {})
        if extracted:
            import json
            st.code(json.dumps(extracted, indent=2), language="json")
        else:
            st.caption("No financial data collected yet...")

        st.markdown("---")
        st.metric("💬 Conversation Turns", len(st.session_state.transcript))

    else:
        st.info("Start a conversation to see debug state here.")

    # ── Leads dashboard ──
    st.markdown("---")
    if st.button("📋 View All Leads", use_container_width=True):
        leads = get_all_leads()
        if leads:
            import pandas as pd
            df = pd.DataFrame(leads)
            st.dataframe(df[[
                "session_id",
                "monthly_income",
                "loan_amount_requested",
                "eligible",
                "handoff_triggered",
                "created_at"
            ]])
        else:
            st.caption("No leads saved yet.")

    # ── Reset ──
    st.markdown("---")
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.agent = LoanCounselorAgent()
        st.session_state.transcript = []
        st.session_state.debug = {}
        st.session_state.session_id = generate_session_id()
        st.rerun()