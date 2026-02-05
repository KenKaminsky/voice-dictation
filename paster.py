"""Auto-paste module for inserting text at cursor position."""

import pyperclip
import time
from pynput.keyboard import Controller, Key
import config


class Paster:
    """Pastes text into the active application."""

    def __init__(self):
        self.keyboard = Controller()

    def paste(self, text: str):
        """Paste text using the configured method."""
        if not text:
            return

        if config.PASTE_METHOD == "clipboard":
            self._paste_via_clipboard(text)
        else:
            self._paste_via_typing(text)

    def _paste_via_clipboard(self, text: str):
        """Paste by copying to clipboard and pressing Cmd+V."""
        # Save current clipboard
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            old_clipboard = None

        # Copy text to clipboard
        pyperclip.copy(text)

        # Small delay to ensure clipboard is ready
        time.sleep(0.05)

        # Press Cmd+V
        self.keyboard.press(Key.cmd)
        self.keyboard.press("v")
        self.keyboard.release("v")
        self.keyboard.release(Key.cmd)

        # Small delay before restoring clipboard
        time.sleep(0.1)

        # Optionally restore old clipboard
        # Commented out to leave transcribed text in clipboard for manual paste
        # if old_clipboard is not None:
        #     pyperclip.copy(old_clipboard)

    def _paste_via_typing(self, text: str):
        """Paste by simulating keystrokes (slower but more compatible)."""
        for char in text:
            self.keyboard.type(char)
            time.sleep(0.005)  # Small delay between characters


# Singleton instance
_paster = None


def get_paster() -> Paster:
    """Get or create the paster singleton."""
    global _paster
    if _paster is None:
        _paster = Paster()
    return _paster


# Test pasting if run directly
if __name__ == "__main__":
    print("Testing paste functionality...")
    print("You have 3 seconds to focus a text field...")
    time.sleep(3)

    paster = get_paster()
    paster.paste("Hello from Voice Dictation! This is a test.")
    print("Text pasted!")
