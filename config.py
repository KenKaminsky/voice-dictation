"""Configuration for Voice Dictation app."""

import json
from pathlib import Path

# Preferences file location
PREFS_DIR = Path.home() / "Library" / "Application Support" / "VoiceDictation"
PREFS_DIR.mkdir(parents=True, exist_ok=True)
PREFS_FILE = PREFS_DIR / "preferences.json"

# Hotkey presets - ID: (display_name, description)
HOTKEY_PRESETS = {
    "fn": ("Fn Key", "Hold Fn to record"),
    "right_cmd": ("Right ⌘", "Hold Right Command to record"),
    "cmd_shift_space": ("⌘⇧ Space", "Hold Cmd+Shift+Space to record"),
    "opt_space": ("⌥ Space", "Hold Option+Space to record"),
    "ctrl_space": ("⌃ Space", "Hold Control+Space to record"),
}

# Default hotkey
DEFAULT_HOTKEY = "fn"


def get_current_hotkey() -> str:
    """Get the current hotkey preset ID."""
    if PREFS_FILE.exists():
        try:
            with open(PREFS_FILE) as f:
                prefs = json.load(f)
                hotkey = prefs.get("hotkey", DEFAULT_HOTKEY)
                if hotkey in HOTKEY_PRESETS:
                    return hotkey
        except Exception:
            pass
    return DEFAULT_HOTKEY


def set_current_hotkey(hotkey_id: str):
    """Set the current hotkey preset."""
    if hotkey_id not in HOTKEY_PRESETS:
        return

    prefs = {}
    if PREFS_FILE.exists():
        try:
            with open(PREFS_FILE) as f:
                prefs = json.load(f)
        except Exception:
            pass

    prefs["hotkey"] = hotkey_id
    with open(PREFS_FILE, "w") as f:
        json.dump(prefs, f, indent=2)


# Audio settings
SAMPLE_RATE = 16000  # Whisper expects 16kHz
CHANNELS = 1

# Transcription model for mlx-whisper
MODEL_ID = "mlx-community/whisper-large-v3-turbo"

# App settings
APP_NAME = "Voice Dictation"
ICON_IDLE = "◉"
ICON_RECORDING = "◉ REC"
ICON_PROCESSING = "◉ ..."

# Paste method: "clipboard" (Cmd+V) or "typing" (simulate keystrokes)
PASTE_METHOD = "clipboard"
