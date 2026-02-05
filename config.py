"""Configuration for Voice Dictation app."""

# Hotkey configuration (Cmd+Shift+Space)
HOTKEY_MODIFIERS = {"cmd", "shift"}
HOTKEY_KEY = "space"

# Audio settings
SAMPLE_RATE = 16000  # Whisper/Voxtral expects 16kHz
CHANNELS = 1

# Transcription model for mlx-whisper
# Options: "mlx-community/whisper-large-v3-turbo", "mlx-community/whisper-large-v3"
MODEL_ID = "mlx-community/whisper-large-v3-turbo"

# App settings
APP_NAME = "Voice Dictation"
# Menu bar icons - using simple text/emoji for visibility
ICON_IDLE = "◉"  # Simple dot when idle
ICON_RECORDING = "◉ REC"  # Orange indicator when recording
ICON_PROCESSING = "◉ ..."  # Processing indicator

# Paste method: "clipboard" (Cmd+V) or "typing" (simulate keystrokes)
PASTE_METHOD = "clipboard"
