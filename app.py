#!/usr/bin/env python3
"""
Voice Dictation App - Wispr Flow-like voice-to-text for macOS

Hold the configured hotkey to record, release to transcribe and paste.
Runs entirely locally using Whisper.
"""

import rumps
import threading
import subprocess
from typing import Optional
import config
from recorder import AudioRecorder, RECORDINGS_DIR
from transcriber import get_transcriber
from paster import get_paster
from storage import get_history
from floating_indicator import get_indicator
from keyboard_handler import HotkeyHandler, get_hotkey_display


class VoiceDictationApp(rumps.App):
    """Menu bar application for voice dictation."""

    def __init__(self):
        # Get current hotkey for display
        hotkey_display = get_hotkey_display()

        # Create menu items first (store references)
        self.status_item = rumps.MenuItem("Status: Ready")
        self.hotkey_item = rumps.MenuItem(f"Hotkey: {hotkey_display}")
        self.history_item = rumps.MenuItem("View History")
        self.load_item = rumps.MenuItem("Load Model Now")

        # Create hotkey submenu
        self.hotkey_menu = rumps.MenuItem("Change Hotkey")
        self._build_hotkey_menu()

        super().__init__(
            name=config.APP_NAME,
            title=config.ICON_IDLE,
            quit_button="Quit",
            menu=[
                self.status_item,
                None,  # Separator
                self.hotkey_item,
                self.hotkey_menu,
                None,  # Separator
                self.history_item,
                self.load_item,
            ],
        )

        # Components
        self.recorder = AudioRecorder()
        self.paster = get_paster()
        self.history = get_history()
        self.indicator = get_indicator()
        self.last_audio_file: Optional[str] = None
        self.last_duration: float = 0

        # State
        self.is_recording = False

        # Start keyboard listener
        self.keyboard_handler = HotkeyHandler(
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )
        self.keyboard_handler.start()

        # Pre-load model in background
        threading.Thread(target=self._preload_model, daemon=True).start()

    def _build_hotkey_menu(self):
        """Build the hotkey selection submenu."""
        current = config.get_current_hotkey()

        for hotkey_id, (name, description) in config.HOTKEY_PRESETS.items():
            # Add checkmark to current selection
            prefix = "✓ " if hotkey_id == current else "   "
            item = rumps.MenuItem(
                f"{prefix}{name}",
                callback=lambda sender, hid=hotkey_id: self._change_hotkey(hid),
            )
            item.hotkey_id = hotkey_id
            self.hotkey_menu.add(item)

    def _change_hotkey(self, hotkey_id: str):
        """Change the active hotkey."""
        config.set_current_hotkey(hotkey_id)

        # Update menu checkmarks
        current = config.get_current_hotkey()
        for item in self.hotkey_menu.values():
            if hasattr(item, 'hotkey_id'):
                name = config.HOTKEY_PRESETS[item.hotkey_id][0]
                prefix = "✓ " if item.hotkey_id == current else "   "
                item.title = f"{prefix}{name}"

        # Update hotkey display
        self.hotkey_item.title = f"Hotkey: {get_hotkey_display()}"

        print(f"Hotkey changed to: {get_hotkey_display()}")

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

    def _on_audio_chunk(self, chunk):
        """Called with each audio chunk during recording."""
        self.indicator.update_waveform(chunk)

    def _on_hotkey_press(self):
        """Called when hotkey is pressed - start recording."""
        if self.is_recording:
            return

        print("Hotkey pressed - starting recording")
        self.is_recording = True
        self.update_icon(config.ICON_RECORDING)
        self.update_status("Recording...")

        # Show floating indicator
        self.indicator.show_recording()

        # Start recording with live audio callback
        self.recorder.start(on_audio_chunk=self._on_audio_chunk)

    def _on_hotkey_release(self):
        """Called when hotkey is released - stop recording and transcribe."""
        if not self.is_recording:
            return

        print("Hotkey released - stopping recording")
        self.is_recording = False
        self.update_icon(config.ICON_PROCESSING)
        self.update_status("Transcribing...")

        # Show processing state
        self.indicator.show_processing()

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
                self.indicator.hide()
                return

            # Transcribe
            transcriber = get_transcriber()
            text = transcriber.transcribe(audio)

            # Hide indicator
            self.indicator.hide()

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
            self.indicator.hide()

        finally:
            self.update_icon(config.ICON_IDLE)

    @rumps.clicked("View History")
    def view_history_clicked(self, sender):
        """Show history window in a separate process."""
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
    hotkey_display = get_hotkey_display()

    print("=" * 50)
    print("Voice Dictation App")
    print("=" * 50)
    print(f"Hotkey: {hotkey_display}")
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
