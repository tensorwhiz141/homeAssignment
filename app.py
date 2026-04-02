# app.py

import streamlit as st
from voice import transcribe_audio, text_to_speech
from agent import LoanAgent
from streamlit_mic_recorder import mic_recorder

# ── PAGE CONFIG ──────────────────────────────────────────
st.set_page_config(page_title="AI Loan Counselor", layout="wide")

# ── SESSION STATE INIT ───────────────────────────────────
if "agent" not in st.session_state:
    st.session_state.agent = LoanAgent()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "locked_language" not in st.session_state:
    st.session_state.locked_language = "english"

# ── TITLE ────────────────────────────────────────────────
st.title("🏦 AI Loan Counselor")

# ── INPUT MODE (VOICE / TEXT) ────────────────────────────
mode = st.radio("Choose Input Mode", ["🎤 Voice", "⌨️ Text"])

# ── USER INPUT VARIABLES ─────────────────────────────────
user_text = ""
audio_bytes = None

# ── TEXT INPUT ───────────────────────────────────────────
if mode == "⌨️ Text":
    user_text = st.text_input("Type your message:")

# ── VOICE INPUT ──────────────────────────────────────────
if mode == "🎤 Voice":
    audio = mic_recorder(start_prompt="🎙️ Click to Record", stop_prompt="⏹️ Stop")

    if audio:
        audio_bytes = audio["bytes"]
        st.write(f"📊 Audio size: {len(audio_bytes)} bytes")

# ── PROCESS FUNCTION ─────────────────────────────────────
def process_message(user_input):

    # Save user message
    st.session_state.chat_history.append(("user", user_input))

    agent_input = {
        "message": user_input,
        "locked_language": st.session_state.locked_language
    }

    result = st.session_state.agent.chat(agent_input)

    response = result.get("response", "⚠️ Error occurred")
    st.session_state.locked_language = result.get("locked_language", "english")

    # Save assistant response
    st.session_state.chat_history.append(("assistant", response))

    # Generate speech
    audio_response = text_to_speech(response, st.session_state.locked_language)

    return response, audio_response, result


# ── MAIN INPUT HANDLING ──────────────────────────────────
user_input = ""

# 🔥 PRIORITY 1: TEXT INPUT
if user_text:
    user_input = user_text.strip()

# 🔥 PRIORITY 2: VOICE INPUT
elif audio_bytes:
    transcript = transcribe_audio(audio_bytes, st.session_state.locked_language)

    if transcript:
        user_input = transcript
    else:
        st.error("❌ Could not transcribe. Try speaking clearly OR use text mode.")

# ── RUN AGENT ────────────────────────────────────────────
if user_input:

    response, audio_response, debug_data = process_message(user_input)

    # ── DISPLAY CURRENT MESSAGE ─────────────────────────
    st.markdown(f"👤 **You:** {user_input}")
    st.markdown(f"🤖 **Assistant:** {response}")

    # ── AUDIO OUTPUT ────────────────────────────────────
    if audio_response:
        st.audio(audio_response, format="audio/wav")

    # ── DEBUG PANEL ─────────────────────────────────────
    with st.expander("🔍 Debug Panel"):
        st.json(debug_data)

# ── CHAT HISTORY ─────────────────────────────────────────
st.markdown("---")
st.subheader("💬 Conversation History")

for role, msg in st.session_state.chat_history:
    if role == "user":
        st.markdown(f"👤 {msg}")
    else:
        st.markdown(f"🤖 {msg}")