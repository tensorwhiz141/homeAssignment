# voice.py
import requests
import streamlit as st
import base64

SARVAM_API_KEY = st.secrets.get("SARVAM_API_KEY")

# ── Language Mapping ─────────────────────────────────────
LANGUAGE_CODE_MAP = {
    "english": "en-IN",
    "hindi":   "hi-IN",
    "marathi": "mr-IN",
    "tamil":   "ta-IN"
}

# ── Speech to Text ───────────────────────────────────────
def transcribe_audio(audio_bytes: bytes, locked_language: str = "english") -> str:
    """
    Speech-to-Text using Sarvam AI saarika:v2 model.
    """

    print("\n========== STT DEBUG ==========")
    print(f"[DEBUG] Audio size: {len(audio_bytes)} bytes")

    language_code = LANGUAGE_CODE_MAP.get(locked_language, "hi-IN")
    print(f"[DEBUG] Language: {language_code}")

    url = "https://api.sarvam.ai/speech-to-text"

    headers = {
        "api-subscription-key": SARVAM_API_KEY
    }

    # ✅ IMPORTANT: Send as WEBM (correct format from mic)
    files = {
        "file": ("audio.webm", audio_bytes, "audio/webm")
    }

    data = {
        "language_code": language_code,
        "model": "saarika:v2",
        "with_timestamps": "false"
    }

    try:
        response = requests.post(url, headers=headers, files=files, data=data)

        print(f"[STT STATUS] {response.status_code}")
        print(f"[STT RESPONSE] {response.text}")

        response.raise_for_status()

        result = response.json()
        transcript = result.get("transcript", "").strip()

        if not transcript:
            print("[WARNING] Empty transcript received")

        print(f"[FINAL TRANSCRIPT] {transcript}")
        print("================================\n")

        return transcript

    except Exception as e:
        print(f"[STT ERROR] {e}")
        print("================================\n")
        return ""


# ── Text to Speech ───────────────────────────────────────
def text_to_speech(text: str, locked_language: str = "english") -> bytes:
    """
    Text-to-Speech using Sarvam AI bulbul:v2 model.
    """

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

        print(f"[TTS STATUS] {response.status_code}")
        print(f"[TTS RESPONSE] {response.text[:200]}")

        response.raise_for_status()
        result = response.json()

        audio_b64 = result.get("audios", [""])[0]

        if audio_b64:
            return base64.b64decode(audio_b64)

        return b""

    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return b""


# ── Helper ───────────────────────────────────────────────
def get_language_code(locked_language: str) -> str:
    return LANGUAGE_CODE_MAP.get(locked_language, "en-IN")