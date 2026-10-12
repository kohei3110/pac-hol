"""Small, auditable checks for fictional voice-agent verification audio."""
from array import array
import hashlib
import math
from pathlib import Path
import sys
import wave


SAMPLE_RATE = 24000
MAX_SECONDS = 30


def read_pcm_fixture(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wav:
        if (
            wav.getnchannels() != 1 or wav.getsampwidth() != 2
            or wav.getframerate() != SAMPLE_RATE or wav.getcomptype() != "NONE"
        ):
            raise ValueError("Use a PCM16 mono WAV at 24 kHz, without compressed audio.")
        if not 0 < wav.getnframes() <= SAMPLE_RATE * MAX_SECONDS:
            raise ValueError("The fictional input fixture must be between 0 and 30 seconds.")
        content = wav.readframes(wav.getnframes())
    if len(content) % 2 or not content:
        raise ValueError("The WAV has no complete PCM16 frames.")
    if audio_summary(content)["rms"] < 1:
        raise ValueError("The input fixture is silent.")
    return content


def audio_summary(content: bytes) -> dict[str, int | float | str]:
    if not content or len(content) % 2:
        raise ValueError("A nonempty complete PCM16 response is required.")
    samples = array("h")
    samples.frombytes(content)
    if sys.byteorder != "little":
        samples.byteswap()
    return {
        "bytes": len(content),
        "seconds": round(len(samples) / SAMPLE_RATE, 3),
        "sampleRate": SAMPLE_RATE,
        "channels": 1,
        "sampleWidth": 2,
        "sha256": hashlib.sha256(content).hexdigest(),
        "rms": round(math.sqrt(sum(sample * sample for sample in samples) / len(samples)), 3),
    }


def write_pcm_wav(path: Path, content: bytes) -> None:
    audio_summary(content)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(content)


def require_turn(result: dict, expected_user: tuple[str, ...], expected_reply: tuple[str, ...]) -> dict:
    if result["status"] != "completed":
        raise ValueError("The response did not complete.")
    if not result["userTranscript"] or not result["assistantTranscript"]:
        raise ValueError("Both input-audio transcription and output transcript must be present.")
    if not all(word in result["userTranscript"] for word in expected_user):
        raise ValueError("The recognized input does not contain the expected scenario terms.")
    if not all(word in result["assistantTranscript"] for word in expected_reply):
        raise ValueError("The spoken reply does not follow the required scenario.")
    if result["audio"]["rms"] < 1 or result["audio"]["seconds"] < 0.1:
        raise ValueError("The completed response must include non-silent audio.")
    if not result["vadStarted"] or not result["vadStopped"]:
        raise ValueError("Both actual server voice-activity transitions are required.")
    return result
