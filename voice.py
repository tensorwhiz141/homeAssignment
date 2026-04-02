# voice.py
import os
import requests
from dotenv import load_dotenv
import io
from pydub import AudioSegment

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

# ── Audio Conversion ─────────────────────────────────────
def convert_to_wav(audio_bytes: bytes) -> bytes:
    """Convert any audio format (WebM, MP4, etc.) to WAV for Sarvam STT."""
    try:
        # Try WebM first (streamlit-mic-recorder format)
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        return wav_io.getvalue()
    except Exception:
        try:
            # Fallback: auto-detect format
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            wav_io = io.BytesIO()
            audio.export(wav_io, format="wav")
            return wav_io.getvalue()
        except Exception as e:
            print(f"[AUDIO CONVERT ERROR] {e}")
            return audio_bytes


# ── Language Mapping ─────────────────────────────────────
LANGUAGE_CODE_MAP = {
    "english": "en-IN",
    "hindi":   "hi-IN",
    "marathi": "mr-IN",
    "tamil":   "ta-IN"
}

SPEAKER_MAP = {
    "english": "meera",
    "hindi":   "meera",
    "marathi": "meera",
    "tamil":   "meera"
}


# ── Speech to Text ───────────────────────────────────────
def transcribe_audio(audio_bytes: bytes, locked_language: str = "english") -> str:
    """
    Speech-to-Text using Sarvam AI saarika:v2 model.
    """

    # ✅ FIX: Convert audio BEFORE sending
    audio_bytes = convert_to_wav(audio_bytes)

    language_code = LANGUAGE_CODE_MAP.get(locked_language, "hi-IN")

    url = "https://api.sarvam.ai/speech-to-text"
    headers = {"api-subscription-key": SARVAM_API_KEY}
    files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
    data = {
        "language_code": language_code,
        "model": "saarika:v2",
        "with_timestamps": "false"
    }

    try:
        response = requests.post(url, headers=headers, files=files, data=data)

        print(f"[STT STATUS] {response.status_code}")
        print(f"[STT RESPONSE] {response.text[:300]}")  # debug

        response.raise_for_status()
        result = response.json()

        transcript = result.get("transcript", "").strip()
        return transcript

    except requests.exceptions.RequestException as e:
        print(f"[STT ERROR] {e}")
        return ""
    except Exception as e:
        print(f"[STT PARSE ERROR] {e}")
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
        print(f"[TTS RESPONSE] {response.text[:300]}")

        response.raise_for_status()
        result = response.json()

        import base64
        audio_b64 = result.get("audios", [""])[0]

        if audio_b64:
            return base64.b64decode(audio_b64)

        return b""

    except requests.exceptions.RequestException as e:
        print(f"[TTS ERROR] {e}")
        return b""
    except Exception as e:
        print(f"[TTS PARSE ERROR] {e}")
        return b""


# ── Helper ───────────────────────────────────────────────
def get_language_code(locked_language: str) -> str:
    return LANGUAGE_CODE_MAP.get(locked_language, "en-IN")