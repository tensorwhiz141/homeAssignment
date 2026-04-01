# app.py
import streamlit as st
from agent import LoanCounselorAgent
from voice import transcribe_audio, text_to_speech
from rag import retrieve_context, is_policy_question

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


# ── Core pipeline function ────────────────────────────────
def process_message(user_message: str):
    """Message → RAG → LLM → TTS → update state."""

    # RAG: inject context if policy question
    agent_input = user_message
    if is_policy_question(user_message):
        rag_context = retrieve_context(user_message)
        if rag_context:
            agent_input = f"[POLICY CONTEXT: {rag_context}]\n\nUser: {user_message}"

    # Add user message to transcript
    st.session_state.transcript.append({
        "role": "user",
        "text": user_message
    })

    # LLM response
    with st.spinner("🤔 Thinking..."):
        result = st.session_state.agent.chat(agent_input)

    response_text = result["response"]
    st.session_state.debug = result

    # TTS
    with st.spinner("🔊 Generating voice response..."):
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


# ── Layout ────────────────────────────────────────────────
st.title("🏠 HomeFirst Vernacular Loan Counselor")
st.caption("Speak or type in English, Hindi, Marathi, or Tamil")

# Handoff banner
if st.session_state.debug.get("handoff_triggered"):
    st.error("🚨 [HANDOFF TRIGGERED: Routing to Human RM]")

col_chat, col_debug = st.columns([2, 1])

# ── LEFT: Chat ────────────────────────────────────────────
with col_chat:
    st.subheader("💬 Conversation")

    # Render transcript
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
        from audio_recorder_streamlit import audio_recorder
        audio_bytes = audio_recorder(
            text="Click to record",
            pause_threshold=2.5,
            sample_rate=16000
        )
        if audio_bytes and len(audio_bytes) > 1000:
            locked_lang = st.session_state.agent.locked_language or "english"
            with st.spinner("🎧 Transcribing..."):
                transcribed = transcribe_audio(audio_bytes, locked_lang)
            if transcribed:
                st.info(f"📝 You said: *{transcribed}*")
                process_message(transcribed)
            else:
                st.warning("Could not transcribe. Please try again or use text input.")
    except ImportError:
        st.warning("Run: pip install audio-recorder-streamlit")

    # ── Text input ──
    st.markdown("#### ⌨️ Or Type Your Message")
    user_text = st.chat_input("Type here in any language...")
    if user_text:
        process_message(user_text)


# ── RIGHT: Debug panel ────────────────────────────────────
with col_debug:
    st.subheader("🔍 LLM Debug Panel")

    d = st.session_state.debug

    if d:
        lang = (d.get("locked_language") or "Detecting...").upper()
        st.metric("🌐 Locked Language", lang)

        tool_status = "✅ Yes" if d.get("tool_called") else "❌ No"
        st.metric("🔧 Tool Called", tool_status)

        handoff_status = "🚨 Triggered" if d.get("handoff_triggered") else "⏳ Pending"
        st.metric("👤 Human Handoff", handoff_status)

        st.markdown("---")
        st.markdown("**📊 Extracted JSON:**")
        extracted = d.get("extracted_data", {})
        if extracted:
            import json
            st.code(json.dumps(extracted, indent=2), language="json")
        else:
            st.caption("No financial data collected yet...")

        st.markdown("---")
        turns = len(st.session_state.transcript)
        st.metric("💬 Conversation Turns", turns)

    else:
        st.info("Start a conversation to see debug state here.")

    st.markdown("---")
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.agent = LoanCounselorAgent()
        st.session_state.transcript = []
        st.session_state.debug = {}
        st.rerun()