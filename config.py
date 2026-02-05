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
ICON_IDLE = "🎤"
ICON_RECORDING = "🔴"
ICON_PROCESSING = "⏳"

# Paste method: "clipboard" (Cmd+V) or "typing" (simulate keystrokes)
PASTE_METHOD = "clipboard"
