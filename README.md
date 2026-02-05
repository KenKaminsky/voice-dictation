# Voice Dictation

A Wispr Flow-like voice-to-text app for macOS. **100% local** - no data leaves your machine.

## How It Works

1. **Hold** `Cmd+Shift+Space` to record
2. **Release** to transcribe
3. Text is **auto-pasted** at your cursor position

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

## First Run

On first run, the app will:
1. Ask for **Accessibility** permissions (needed for global hotkey + paste)
2. Ask for **Microphone** permissions
3. Download the Whisper model (~3GB)

## Configuration

Edit `config.py` to customize:
- **HOTKEY_MODIFIERS / HOTKEY_KEY** - Change the activation hotkey
- **MODEL_ID** - Switch between Whisper and Voxtral
- **PASTE_METHOD** - "clipboard" (Cmd+V) or "typing" (keystroke simulation)

## Menu Bar

The app shows an icon in your menu bar:
- 🎤 Ready (idle)
- 🔴 Recording
- ⏳ Processing

## Models

| Model | Speed | Quality | Size |
|-------|-------|---------|------|
| `openai/whisper-large-v3-turbo` | Fast | Excellent | ~3GB |
| `mistralai/Voxtral-Mini-4B-Realtime-2602` | Faster | Excellent | ~8GB |

## Troubleshooting

### "Accessibility permissions"
Go to **System Settings → Privacy & Security → Accessibility** and add Terminal/your Python app.

### "Microphone permissions"
Go to **System Settings → Privacy & Security → Microphone** and allow Terminal/your Python app.

### Model loading slow
First load downloads the model. Subsequent loads are from cache (~5-10 seconds on M4 Max).
