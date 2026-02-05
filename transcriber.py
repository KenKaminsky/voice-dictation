"""Transcription module using mlx-whisper for Apple Silicon."""

import numpy as np
import mlx_whisper
from typing import Optional
import config


class Transcriber:
    """Transcribes audio using mlx-whisper (optimized for Apple Silicon)."""

    def __init__(self):
        self.model_loaded = False
        print("Using mlx-whisper (Apple Silicon optimized)")

    def load_model(self):
        """Pre-warm the model by running a dummy transcription."""
        if self.model_loaded:
            return

        print(f"Loading model: {config.MODEL_ID}...")
        print("This may take a moment on first run...")

        # Warm up by transcribing silence
        dummy_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
        mlx_whisper.transcribe(
            dummy_audio,
            path_or_hf_repo=config.MODEL_ID,
        )

        self.model_loaded = True
        print("Model loaded successfully!")

    def transcribe(self, audio: np.ndarray) -> Optional[str]:
        """Transcribe audio array to text."""
        if audio is None or len(audio) == 0:
            return None

        # Ensure audio is float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Normalize audio if needed
        if np.abs(audio).max() > 1.0:
            audio = audio / np.abs(audio).max()

        print(f"Transcribing... (audio length: {len(audio)}, max: {np.abs(audio).max():.4f})")

        # Run transcription with mlx-whisper
        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=config.MODEL_ID,
            language="en",
        )

        text = result.get("text", "").strip()
        print(f"Transcribed: {text}")

        return text


# Singleton instance
_transcriber: Optional[Transcriber] = None


def get_transcriber() -> Transcriber:
    """Get or create the transcriber singleton."""
    global _transcriber
    if _transcriber is None:
        _transcriber = Transcriber()
    return _transcriber


# Test transcription if run directly
if __name__ == "__main__":
    import sounddevice as sd

    print("Recording 5 seconds of audio for transcription test...")
    print("Speak clearly into the microphone...")

    # Record audio
    duration = 5
    sample_rate = config.SAMPLE_RATE
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32)
    sd.wait()
    audio = audio.flatten()

    print(f"Recorded audio shape: {audio.shape}")
    print(f"Max amplitude: {np.abs(audio).max():.4f}")

    # Transcribe
    transcriber = get_transcriber()
    text = transcriber.transcribe(audio)
    print(f"Result: '{text}'")
