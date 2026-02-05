#!/usr/bin/env python3
"""
Voice Dictation App - Wispr Flow-like voice-to-text for macOS

Hold Cmd+Shift+Space to record, release to transcribe and paste.
Runs entirely locally using Whisper/Voxtral.
"""

import rumps
import threading
import subprocess
from pynput import keyboard
from typing import Optional
import config
from recorder import AudioRecorder, RECORDINGS_DIR
from transcriber import get_transcriber
from paster import get_paster
from storage import get_history


class VoiceDictationApp(rumps.App):
    """Menu bar application for voice dictation."""

    def __init__(self):
        # Create menu items first (store references)
        self.status_item = rumps.MenuItem("Status: Ready")
        self.hotkey_item = rumps.MenuItem("Hotkey: Cmd+Shift+Space")
        self.history_item = rumps.MenuItem("View History")
        self.load_item = rumps.MenuItem("Load Model Now")

        super().__init__(
            name=config.APP_NAME,
            title=config.ICON_IDLE,
            quit_button="Quit",
            menu=[
                self.status_item,
                None,  # Separator
                self.hotkey_item,
                None,  # Separator
                self.history_item,
                self.load_item,
            ],
        )

        # Components
        self.recorder = AudioRecorder()
        self.paster = get_paster()
        self.history = get_history()
        self.last_audio_file: Optional[str] = None
        self.last_duration: float = 0

        # State
        self.is_recording = False
        self.held_keys = set()
        self.hotkey_active = False

        # Start keyboard listener in background
        self.start_keyboard_listener()

        # Pre-load model in background
        threading.Thread(target=self._preload_model, daemon=True).start()

    def _preload_model(self):
        """Pre-load the transcription model in background."""
        self.update_status("Loading model...")
        try:
            get_transcriber().load_model()
            self.update_status("Ready")
        except Exception as e:
            self.update_status(f"Model error: {str(e)[:30]}")
            print(f"Error loading model: {e}")

    def update_status(self, status: str):
        """Update the status menu item."""
        self.status_item.title = f"Status: {status}"

    def update_icon(self, icon: str):
        """Update the menu bar icon."""
        self.title = icon

    def start_keyboard_listener(self):
        """Start the global keyboard listener."""

        def on_press(key):
            # Track held keys
            key_name = self._get_key_name(key)
            if key_name:
                self.held_keys.add(key_name)

            # Check if hotkey combination is pressed
            if self._is_hotkey_pressed() and not self.hotkey_active:
                self.hotkey_active = True
                self._on_hotkey_press()

        def on_release(key):
            key_name = self._get_key_name(key)
            if key_name and key_name in self.held_keys:
                self.held_keys.discard(key_name)

            # Check if hotkey was released
            if self.hotkey_active and not self._is_hotkey_pressed():
                self.hotkey_active = False
                self._on_hotkey_release()

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.daemon = True
        listener.start()
        print("Keyboard listener started")

    def _get_key_name(self, key) -> Optional[str]:
        """Convert pynput key to string name."""
        try:
            if hasattr(key, "char") and key.char:
                return key.char.lower()
            elif hasattr(key, "name"):
                return key.name.lower()
            elif key == keyboard.Key.cmd or key == keyboard.Key.cmd_l or key == keyboard.Key.cmd_r:
                return "cmd"
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                return "shift"
            elif key == keyboard.Key.space:
                return "space"
        except Exception:
            pass
        return None

    def _is_hotkey_pressed(self) -> bool:
        """Check if the hotkey combination is currently pressed."""
        required = config.HOTKEY_MODIFIERS | {config.HOTKEY_KEY}
        return required.issubset(self.held_keys)

    def _on_hotkey_press(self):
        """Called when hotkey is pressed - start recording."""
        if self.is_recording:
            return

        print("Hotkey pressed - starting recording")
        self.is_recording = True
        self.update_icon(config.ICON_RECORDING)
        self.update_status("Recording...")
        self.recorder.start()

    def _on_hotkey_release(self):
        """Called when hotkey is released - stop recording and transcribe."""
        if not self.is_recording:
            return

        print("Hotkey released - stopping recording")
        self.is_recording = False
        self.update_icon(config.ICON_PROCESSING)
        self.update_status("Transcribing...")

        # Stop recording and get audio
        audio = self.recorder.stop()

        # Get the saved audio file path and duration
        if hasattr(self.recorder, 'last_saved_file'):
            self.last_audio_file = str(self.recorder.last_saved_file)
        if audio is not None:
            self.last_duration = len(audio) / config.SAMPLE_RATE

        # Transcribe in background to not block UI
        threading.Thread(target=self._transcribe_and_paste, args=(audio,), daemon=True).start()

    def _transcribe_and_paste(self, audio):
        """Transcribe audio and paste result."""
        try:
            if audio is None or len(audio) < config.SAMPLE_RATE * 0.3:  # Less than 0.3 seconds
                print("Audio too short, skipping")
                self.update_status("Ready (audio too short)")
                self.update_icon(config.ICON_IDLE)
                return

            # Transcribe
            transcriber = get_transcriber()
            text = transcriber.transcribe(audio)

            if text:
                # Save to history
                self.history.add(
                    text=text,
                    duration_seconds=self.last_duration,
                    audio_file=self.last_audio_file,
                )

                # Paste the text
                self.update_status("Pasting...")
                self.paster.paste(text)
                self.update_status("Ready")
                print(f"Pasted: {text}")
            else:
                self.update_status("Ready (no speech detected)")

        except Exception as e:
            print(f"Transcription error: {e}")
            self.update_status(f"Error: {str(e)[:30]}")

        finally:
            self.update_icon(config.ICON_IDLE)

    @rumps.clicked("View History")
    def view_history_clicked(self, sender):
        """Show history window in a separate process."""
        import subprocess
        import sys
        import os

        # Launch history viewer as separate process
        app_dir = os.path.dirname(os.path.abspath(__file__))
        viewer_path = os.path.join(app_dir, "history_viewer.py")
        venv_python = os.path.join(app_dir, "venv", "bin", "python")

        subprocess.Popen([venv_python, viewer_path])

    @rumps.clicked("Load Model Now")
    def load_model_clicked(self, sender):
        """Manually trigger model loading."""
        threading.Thread(target=self._preload_model, daemon=True).start()


def main():
    """Main entry point."""
    print("=" * 50)
    print("Voice Dictation App")
    print("=" * 50)
    print(f"Hotkey: Cmd+Shift+Space (hold to record)")
    print(f"Model: {config.MODEL_ID}")
    print("=" * 50)
    print()
    print("Starting app...")
    print("Grant accessibility permissions if prompted.")
    print()

    app = VoiceDictationApp()
    app.run()


if __name__ == "__main__":
    main()
