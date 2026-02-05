"""Audio recording module using sounddevice."""

import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from threading import Event
from typing import Optional
from pathlib import Path
from datetime import datetime
import config

# Directory to save recordings for debugging
RECORDINGS_DIR = Path(__file__).parent / "recordings"
RECORDINGS_DIR.mkdir(exist_ok=True)


class AudioRecorder:
    """Records audio from microphone into a numpy array."""

    def __init__(self):
        self.sample_rate = config.SAMPLE_RATE
        self.channels = config.CHANNELS
        self.recording = False
        self.audio_data: list[np.ndarray] = []
        self.stop_event = Event()
        self.last_saved_file: Optional[Path] = None

    def start(self):
        """Start recording audio."""
        self.recording = True
        self.audio_data = []
        self.stop_event.clear()

        def callback(indata, frames, time, status):
            if status:
                print(f"Recording status: {status}")
            if self.recording:
                self.audio_data.append(indata.copy())

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
            callback=callback,
        )
        self.stream.start()
        print("Recording started...")

    def stop(self) -> Optional[np.ndarray]:
        """Stop recording and return audio as numpy array."""
        if not self.recording:
            return None

        self.recording = False
        self.stream.stop()
        self.stream.close()
        print("Recording stopped.")

        if not self.audio_data:
            return None

        # Concatenate all chunks into single array
        audio = np.concatenate(self.audio_data, axis=0)
        # Flatten to 1D if needed
        if audio.ndim > 1:
            audio = audio.flatten()

        duration = len(audio) / self.sample_rate
        max_amp = np.abs(audio).max()
        print(f"Recorded {duration:.2f} seconds of audio (max amplitude: {max_amp:.4f})")

        # Save recording to disk
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = RECORDINGS_DIR / f"recording_{timestamp}.wav"
        # Convert float32 [-1, 1] to int16 for WAV
        audio_int16 = (audio * 32767).astype(np.int16)
        wavfile.write(filepath, self.sample_rate, audio_int16)
        self.last_saved_file = filepath
        print(f"Saved recording to: {filepath}")

        return audio

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self.recording


# Test recording if run directly
if __name__ == "__main__":
    import time

    recorder = AudioRecorder()
    print("Recording for 3 seconds...")
    recorder.start()
    time.sleep(3)
    audio = recorder.stop()

    if audio is not None:
        print(f"Audio shape: {audio.shape}")
        print(f"Audio dtype: {audio.dtype}")
        print(f"Sample rate: {config.SAMPLE_RATE}")
