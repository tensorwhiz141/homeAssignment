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
    """Convert audio to proper PCM WAV format for Sarvam."""
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")

        # ✅ FORCE correct format
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

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

    print("\n========== STT DEBUG START ==========")

    # Convert audio
    audio_bytes = convert_to_wav(audio_bytes)
    print(f"[DEBUG] Audio bytes after conversion: {len(audio_bytes)}")

    language_code = LANGUAGE_CODE_MAP.get(locked_language, "hi-IN")
    print(f"[DEBUG] Language Code: {language_code}")

    url = "https://api.sarvam.ai/speech-to-text"
    headers = {"api-subscription-key": SARVAM_API_KEY}

    files = {
        "file": ("audio.wav", audio_bytes, "audio/wav")
    }

    data = {
        "language_code": language_code,
        "model": "saarika:v2",
        "with_timestamps": "false"
    }

    try:
        print("[DEBUG] Sending request to Sarvam...")

        response = requests.post(url, headers=headers, files=files, data=data)

        print(f"[STT STATUS] {response.status_code}")
        print(f"[STT HEADERS] {response.headers}")

        # 🔥 IMPORTANT: Print FULL response (not truncated)
        print(f"[STT RESPONSE FULL] {response.text}")

        response.raise_for_status()

        result = response.json()
        print(f"[STT PARSED JSON] {result}")

        transcript = result.get("transcript", "").strip()

        if not transcript:
            print("[WARNING] Empty transcript received!")

        print(f"[FINAL TRANSCRIPT] {transcript}")
        print("========== STT DEBUG END ==========\n")

        return transcript

    except requests.exceptions.RequestException as e:
        print(f"[STT ERROR - REQUEST FAILED] {e}")
        print("========== STT DEBUG END ==========\n")
        return ""

    except Exception as e:
        print(f"[STT ERROR - PARSE FAILED] {e}")
        print("========== STT DEBUG END ==========\n")
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