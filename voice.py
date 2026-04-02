# voice.py

import requests
import streamlit as st
import base64
from pydub import AudioSegment
import io

# ── API KEY ──────────────────────────────────────────────
SARVAM_API_KEY = st.secrets.get("SARVAM_API_KEY")

# ── Language Mapping ─────────────────────────────────────
LANGUAGE_CODE_MAP = {
    "english": "en-IN",
    "hindi":   "hi-IN",
    "marathi": "mr-IN",
    "tamil":   "ta-IN"
}

# ── Speech to Text (SARVAM) ──────────────────────────────
def transcribe_audio(audio_bytes: bytes, locked_language: str = "english") -> str:

    print("\n========== STT DEBUG ==========")
    print("Raw audio size:", len(audio_bytes))

    # Safety checks
    if not SARVAM_API_KEY:
        print("❌ SARVAM_API_KEY missing")
        return ""

    if not audio_bytes or len(audio_bytes) < 1000:
        print("❌ Audio too small")
        return ""

    # 🔥 FORCE PROPER DECODE + PCM FIX
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")

        audio = (
            audio
            .set_frame_rate(16000)   # 16kHz
            .set_channels(1)         # mono
            .set_sample_width(2)     # 16-bit PCM 🔥 IMPORTANT
        )

        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")

        wav_bytes = wav_io.getvalue()

        print("✅ Conversion success")
        print("WAV size:", len(wav_bytes))

    except Exception as e:
        print("❌ Conversion error:", e)
        return ""

    # ── SARVAM API ───────────────────────────────────────
    url = "https://api.sarvam.ai/speech-to-text"

    headers = {
        "api-subscription-key": SARVAM_API_KEY
    }

    files = {
        "file": ("audio.wav", wav_bytes, "audio/wav")
    }

    data = {
        "language_code": LANGUAGE_CODE_MAP.get(locked_language, "en-IN"),
        "model": "saarika:v2",
        "with_timestamps": "false"
    }

    try:
        print("🚀 Sending to Sarvam...")
        print("Bytes being sent:", len(wav_bytes))

        response = requests.post(url, headers=headers, files=files, data=data)

        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)

        response.raise_for_status()

        result = response.json()
        transcript = result.get("transcript", "").strip()

        if not transcript:
            print("⚠️ Empty transcript")

        print("✅ FINAL TEXT:", transcript)
        print("================================\n")

        return transcript

    except Exception as e:
        print("❌ STT ERROR:", e)
        return ""


# ── Text to Speech (SARVAM) ──────────────────────────────
def text_to_speech(text: str, locked_language: str = "english") -> bytes:

    if not SARVAM_API_KEY:
        print("❌ SARVAM_API_KEY missing")
        return b""

    language_code = LANGUAGE_CODE_MAP.get(locked_language, "en-IN")

    url = "https://api.sarvam.ai/text-to-speech"

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": [text[:500]],
        "target_language_code": language_code,
        "speaker": "anushka",
        "model": "bulbul:v2",
        "pitch": 0,
        "pace": 1.0,
        "loudness": 1.5,
        "speech_sample_rate": 22050,
        "enable_preprocessing": True
    }

    try:
        response = requests.post(url, headers=headers, json=payload)

        print("[TTS STATUS]:", response.status_code)

        response.raise_for_status()

        result = response.json()
        audio_b64 = result.get("audios", [""])[0]

        if audio_b64:
            return base64.b64decode(audio_b64)

        return b""

    except Exception as e:
        print("❌ TTS ERROR:", e)
        return b""