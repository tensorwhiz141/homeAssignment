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
import io
import wave

def transcribe_audio(audio_bytes: bytes, locked_language: str = "english") -> str:
    """
    Convert raw mic audio → proper WAV → send to Sarvam
    """

    print("\n========== STT DEBUG ==========")
    print(f"[DEBUG] Raw audio size: {len(audio_bytes)}")

    language_code = LANGUAGE_CODE_MAP.get(locked_language, "hi-IN")

    # 🔥 Convert to proper WAV (PCM)
    try:
        wav_buffer = io.BytesIO()

        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(1)       # mono
            wf.setsampwidth(2)       # 16-bit
            wf.setframerate(16000)   # 16kHz
            wf.writeframes(audio_bytes)

        wav_bytes = wav_buffer.getvalue()
        print(f"[DEBUG] WAV size: {len(wav_bytes)}")

    except Exception as e:
        print(f"[WAV ERROR] {e}")
        wav_bytes = audio_bytes  # fallback

    url = "https://api.sarvam.ai/speech-to-text"

    headers = {
        "api-subscription-key": SARVAM_API_KEY
    }

    files = {
        "file": ("audio.wav", wav_bytes, "audio/wav")
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
            print("⚠️ EMPTY TRANSCRIPT")

        print(f"[FINAL] {transcript}")
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