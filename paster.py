"""Auto-paste module for inserting text at cursor position."""

import time
import Quartz
from AppKit import NSPasteboard, NSPasteboardTypeString
import config


class Paster:
    """Pastes text into the active application using native macOS APIs."""

    def paste(self, text: str):
        """Paste text using the configured method."""
        if not text:
            return

        if config.PASTE_METHOD == "clipboard":
            self._paste_via_clipboard(text)
        else:
            self._paste_via_typing(text)

    def _paste_via_clipboard(self, text: str):
        """Paste by copying to clipboard and simulating Cmd+V with Quartz."""
        # Copy to clipboard using native API
        pasteboard = NSPasteboard.generalPasteboard()
        pasteboard.clearContents()
        pasteboard.setString_forType_(text, NSPasteboardTypeString)

        # Small delay to ensure clipboard is ready
        time.sleep(0.1)

        # Simulate Cmd+V using Quartz (more reliable than pynput)
        # Key code 9 = 'v'
        v_keycode = 9

        # Create key down event for 'v' with Cmd modifier
        cmd_v_down = Quartz.CGEventCreateKeyboardEvent(None, v_keycode, True)
        Quartz.CGEventSetFlags(cmd_v_down, Quartz.kCGEventFlagMaskCommand)

        # Create key up event
        cmd_v_up = Quartz.CGEventCreateKeyboardEvent(None, v_keycode, False)
        Quartz.CGEventSetFlags(cmd_v_up, Quartz.kCGEventFlagMaskCommand)

        # Post the events
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, cmd_v_down)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, cmd_v_up)

        print(f"Auto-pasted: {text[:50]}...")

    def _paste_via_typing(self, text: str):
        """Paste by simulating keystrokes (slower but more compatible)."""
        for char in text:
            # Get unicode value
            unicode_char = ord(char)

            # Create key events for the character
            key_down = Quartz.CGEventCreateKeyboardEvent(None, 0, True)
            Quartz.CGEventKeyboardSetUnicodeString(key_down, 1, char)

            key_up = Quartz.CGEventCreateKeyboardEvent(None, 0, False)
            Quartz.CGEventKeyboardSetUnicodeString(key_up, 1, char)

            Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_down)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_up)

            time.sleep(0.01)  # Small delay between characters


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
    print("You have 3 seconds to click into a text field...")
    time.sleep(3)

    paster = get_paster()
    paster.paste("Hello from Voice Dictation! This is a test.")
    print("Text pasted!")
