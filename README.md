# Voice Dictation for macOS

A Wispr Flow-like voice-to-text application for macOS that runs entirely locally. Hold a hotkey to record, release to transcribe and auto-paste. No cloud services, no subscriptions, no data leaves your machine.

![macOS](https://img.shields.io/badge/macOS-Sonoma%2B-blue)
![Apple Silicon](https://img.shields.io/badge/Apple%20Silicon-M1%2FM2%2FM3%2FM4-green)
![Python](https://img.shields.io/badge/Python-3.9%2B-yellow)

## Features

- **Hold-to-Record**: Hold the Fn key (or configurable hotkey) to record, release to transcribe
- **Instant Paste**: Transcribed text is automatically pasted at your cursor position
- **Fully Local**: Uses MLX-Whisper optimized for Apple Silicon - no internet required
- **Live Waveform**: Floating indicator shows recording status with smooth audio visualization
- **History Viewer**: Native macOS window with search, stats, and audio playback
- **Configurable Hotkeys**: Choose from 5 preset hotkey combinations
- **Menu Bar App**: Runs quietly in the background, accessible from the menu bar

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Usage](#usage)
4. [Architecture](#architecture)
5. [Project Structure](#project-structure)
6. [How the Model Works](#how-the-model-works)
7. [UI Components](#ui-components)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)
10. [Future Deployment Options](#future-deployment-options)
11. [Development](#development)

---

## System Requirements

| Requirement | Details |
|-------------|---------|
| **macOS** | Ventura 13.0+ (Sonoma 14.0+ recommended) |
| **Processor** | Apple Silicon (M1, M2, M3, M4) - **Intel not supported** |
| **RAM** | 8GB minimum, 16GB+ recommended |
| **Disk Space** | ~2GB for Whisper model (downloaded on first run) |
| **Permissions** | Accessibility (for hotkeys) + Microphone (for recording) |

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/KenKaminsky/voice-dictation.git
cd voice-dictation
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. First Run (Downloads Model)

```bash
python app.py
```

The first run downloads the Whisper model (~1.5GB). Grant Accessibility and Microphone permissions when prompted.

### 5. Create App Bundle (Optional - for Spotlight)

To launch from Spotlight, create an app bundle:

```bash
mkdir -p "/Applications/Voice Dictation.app/Contents/MacOS"

cat > "/Applications/Voice Dictation.app/Contents/MacOS/Voice Dictation" << 'EOF'
#!/bin/bash
cd /Users/YOUR_USERNAME/Personal-Notebooks/voice-dictation
source venv/bin/activate
exec python app.py
EOF

chmod +x "/Applications/Voice Dictation.app/Contents/MacOS/Voice Dictation"

cat > "/Applications/Voice Dictation.app/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Voice Dictation</string>
    <key>CFBundleIdentifier</key>
    <string>com.local.voicedictation</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
EOF
```

Replace `YOUR_USERNAME` with your macOS username.

---

## Usage

### Basic Operation

1. **Start**: Launch "Voice Dictation" from Spotlight or run `python app.py`
2. **Record**: Hold the **Fn key** (default) while speaking
3. **Transcribe**: Release the key - text appears at your cursor

### Menu Bar Options

Click the ◉ icon in the menu bar:

| Option | Description |
|--------|-------------|
| Status | Shows current state (Ready, Recording, Transcribing) |
| Hotkey | Displays current hotkey binding |
| Change Hotkey | Select from 5 preset options |
| View History | Opens native history browser |
| Load Model Now | Manually trigger model loading |
| Quit | Exit the application |

### Hotkey Options

| Hotkey | Description |
|--------|-------------|
| **Fn Key** | Hold Fn to record (default) |
| **Right ⌘** | Hold Right Command to record |
| **⌘⇧ Space** | Hold Cmd+Shift+Space to record |
| **⌥ Space** | Hold Option+Space to record |
| **⌃ Space** | Hold Control+Space to record |

Your selection is saved and persists across restarts.

### History Viewer

Click "View History" in the menu to open the native history browser:

- **Stats Header**: Total recordings, words, recording time, and average WPM
- **Search**: Filter transcriptions by keyword (matches are highlighted in yellow)
- **Copy**: Click the copy icon (doc.on.doc) to copy any transcription
- **Play**: Click the play icon to replay the original audio recording
- **Timestamps**: Shows relative time ("5 mins ago") with full date on hover

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Menu Bar App                             │
│                        (rumps + AppKit)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   Keyboard   │  │   Audio      │  │   Floating           │   │
│  │   Handler    │  │   Recorder   │  │   Indicator          │   │
│  │              │  │              │  │                      │   │
│  │ Quartz Event │  │ sounddevice  │  │ NSWindow + NSView    │   │
│  │ Tap (Fn key) │  │ 16kHz mono   │  │ Live waveform        │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘   │
│         │                 │                                      │
│         ▼                 ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Transcriber                            │   │
│  │                                                           │   │
│  │  MLX-Whisper (large-v3-turbo)                            │   │
│  │  - Apple Silicon optimized (Neural Engine)               │   │
│  │  - ~1.5GB model                                          │   │
│  │  - ~2-3s for typical recordings                          │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   Paster     │  │   Storage    │  │   History Viewer     │   │
│  │              │  │              │  │                      │   │
│  │ Clipboard +  │  │ JSON file    │  │ Native AppKit        │   │
│  │ Cmd+V        │  │ + WAV audio  │  │ SF Symbols           │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Hotkey Detection**: `keyboard_handler.py` uses Quartz CGEventTap to detect Fn key (or other configured hotkey) at the system level
2. **Audio Recording**: `recorder.py` captures 16kHz mono audio using sounddevice, streaming chunks to the waveform display
3. **Transcription**: `transcriber.py` feeds audio to MLX-Whisper running on the Neural Engine
4. **Output**: `paster.py` copies text to clipboard and simulates Cmd+V
5. **Storage**: `storage.py` saves transcription + audio to JSON/WAV files

---

## Project Structure

```
voice-dictation/
├── app.py                 # Main entry point, menu bar app (rumps)
├── config.py              # Configuration, preferences, hotkey presets
├── keyboard_handler.py    # Quartz event tap for Fn key and hotkeys
├── recorder.py            # Audio recording with sounddevice
├── transcriber.py         # MLX-Whisper transcription service
├── paster.py              # Clipboard and Cmd+V paste automation
├── storage.py             # JSON-based history storage
├── floating_indicator.py  # Live recording indicator (NSWindow/NSView)
├── history_viewer.py      # Native history browser (AppKit, SF Symbols)
├── requirements.txt       # Python dependencies
├── venv/                  # Virtual environment (not in git)
└── recordings/            # Saved audio files (WAV format)
```

### Key Files Explained

| File | Purpose |
|------|---------|
| `app.py` | Main application class, coordinates all components, handles menu |
| `keyboard_handler.py` | Low-level keyboard capture using Quartz CGEventTap for Fn key support |
| `floating_indicator.py` | Custom NSView that draws smooth waveform bars during recording |
| `history_viewer.py` | Full AppKit application with NSScrollView, search, SF Symbols |
| `config.py` | Hotkey presets, preferences file I/O, app constants |

---

## How the Model Works

### MLX-Whisper

This app uses [MLX-Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper), Apple's optimized implementation of OpenAI's Whisper model for Apple Silicon.

**Model Used**: `mlx-community/whisper-large-v3-turbo`

| Attribute | Value |
|-----------|-------|
| Parameters | 809M (distilled from large-v3's 1.5B) |
| Architecture | Encoder-decoder transformer |
| Optimization | Apple Neural Engine + GPU |
| Languages | 99 (English optimized) |
| Input Format | 16kHz mono audio |

### Processing Pipeline

```
Audio Input (16kHz)
    │
    ▼
┌─────────────────────┐
│  Log-Mel Spectrogram │  ← 80 mel bins, 25ms windows
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Encoder (Transformer) │  ← 32 layers, processes full audio
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Decoder (Transformer) │  ← 2 layers, autoregressive text generation
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Beam Search Decoding │  ← Selects best text sequence
└─────────────────────┘
    │
    ▼
Transcribed Text
```

### Performance Benchmarks (M4 Max)

| Metric | Value |
|--------|-------|
| Model Load | ~2 seconds (from cache) |
| First Load | ~30 seconds (download + compile) |
| Transcription Speed | ~0.3x real-time |
| 10s Recording | ~3s to transcribe |
| Memory Usage | ~2GB VRAM |

---

## UI Components

### Floating Indicator

A small pill-shaped overlay (180×36 pixels) that appears during recording:

- **Position**: Bottom center of the active screen (follows mouse to correct display)
- **Recording State**: Orange waveform bars (20 bars with RMS smoothing) + "REC" label
- **Processing State**: Blue pulsing sine wave animation + "..." label
- **Background**: Dark semi-transparent (#1A1A1A at 95% opacity)
- **Corner Radius**: Fully rounded pill shape

Implementation: `floating_indicator.py` using `NSWindow` + custom `NSView.drawRect_()`

### Menu Bar Icon

| State | Icon | Meaning |
|-------|------|---------|
| Ready | ◉ | Idle, ready to record |
| Recording | ◉ REC | Currently recording |
| Processing | ◉ ... | Transcribing audio |

### History Viewer Window

A native macOS window (720×640 default) with:

- **Stats Bar**: Four metrics with SF Symbol icons (waveform, text.word.spacing, clock, speedometer)
- **Search Field**: NSSearchField with live filtering
- **Entry Cards**: Rounded rect cards with metadata, copy button, play button
- **Icons**: Native SF Symbols (doc.on.doc, play.fill, pause.fill, checkmark)
- **Colors**: Uses system colors (NSColor.labelColor, NSColor.secondaryLabelColor) for dark/light mode support

---

## Configuration

### Preferences Location

```
~/Library/Application Support/VoiceDictation/
├── preferences.json    # {"hotkey": "fn"}
└── history.json        # Array of transcription entries
```

### Audio Recordings Location

```
<project-dir>/recordings/
└── recording_YYYYMMDD_HHMMSS.wav   # 16kHz mono WAV files
```

### config.py Options

```python
# Audio settings
SAMPLE_RATE = 16000  # Required for Whisper - don't change
CHANNELS = 1         # Mono audio

# Model selection
MODEL_ID = "mlx-community/whisper-large-v3-turbo"
# Alternative: "mlx-community/whisper-large-v3" (larger, slightly better)

# Paste method
PASTE_METHOD = "clipboard"  # Copy to clipboard + Cmd+V
# Alternative: "typing"     # Simulate individual keystrokes

# Hotkey presets available
HOTKEY_PRESETS = {
    "fn": ("Fn Key", "Hold Fn to record"),
    "right_cmd": ("Right ⌘", "Hold Right Command to record"),
    "cmd_shift_space": ("⌘⇧ Space", "Hold Cmd+Shift+Space to record"),
    "opt_space": ("⌥ Space", "Hold Option+Space to record"),
    "ctrl_space": ("⌃ Space", "Hold Control+Space to record"),
}
```

---

## Troubleshooting

### "Failed to create event tap"

**Cause**: Missing Accessibility permissions

**Fix**: System Settings → Privacy & Security → Accessibility → Add and enable Terminal (or Python)

### Model not loading / Download stuck

**Cause**: Network issue or disk space

**Fix**:
- Ensure ~2GB free disk space
- Check internet connection
- Try: `rm -rf ~/.cache/huggingface/hub/models--mlx-community--whisper*`

### Audio not recording

**Cause**: Missing Microphone permissions

**Fix**: System Settings → Privacy & Security → Microphone → Enable for Terminal/Python

### Transcription is slow or garbled

**Cause**: Running on Intel Mac or wrong audio format

**Fix**:
- Ensure Apple Silicon Mac (M1/M2/M3/M4)
- Check audio input device in System Settings → Sound

### Hotkey not working

**Cause**: Another app capturing the key, or Fn key set to special function

**Fix**:
- Try a different hotkey preset from the menu
- Check System Settings → Keyboard → "Press Fn key to" setting
- Ensure app has Accessibility permissions

---

## Future Deployment Options

### Current State (Development)

The app currently runs from source with a thin .app wrapper. Updates are instant via `git pull`.

### Option 1: py2app (Standalone Bundle)

Bundle Python + all dependencies into a self-contained .app:

```bash
pip install py2app

# Create setup.py for py2app
cat > setup.py << 'EOF'
from setuptools import setup

APP = ['app.py']
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'CFBundleName': 'Voice Dictation',
        'CFBundleIdentifier': 'com.kenkaminsky.voicedictation',
        'LSUIElement': True,
    },
    'packages': ['mlx', 'mlx_whisper', 'rumps', 'sounddevice'],
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
EOF

python setup.py py2app
```

**Pros**: No Python installation needed, double-click to run
**Cons**: Large bundle (500MB+), requires code signing for Gatekeeper

### Option 2: DMG Distribution (Signed)

For public distribution:

1. **Apple Developer Account** ($99/year)
2. **Code sign**: `codesign --deep --force --sign "Developer ID Application: Name" app.app`
3. **Notarize**: `xcrun notarytool submit app.zip --apple-id X --password X`
4. **Create DMG**: Use `create-dmg` tool

### Option 3: Homebrew Tap

For developer-friendly distribution:

```ruby
# Formula: voice-dictation.rb
class VoiceDictation < Formula
  desc "Local voice-to-text for macOS"
  homepage "https://github.com/KenKaminsky/voice-dictation"
  url "https://github.com/KenKaminsky/voice-dictation/archive/v1.0.0.tar.gz"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources
  end
end
```

### Requirements for Others to Run

| Requirement | Notes |
|-------------|-------|
| Apple Silicon Mac | M1, M2, M3, or M4 chip required |
| macOS 13+ | Ventura or newer |
| ~4GB disk space | 2GB model + dependencies |
| Grant permissions | Accessibility + Microphone |

---

## Development

### Running from Source

```bash
cd voice-dictation
source venv/bin/activate
python app.py
```

### Testing Individual Components

```bash
# Test audio recording (records 3 seconds)
python recorder.py

# Test keyboard handler (prints when hotkey pressed)
python keyboard_handler.py

# Test history viewer (opens window)
python history_viewer.py

# Test transcription
python -c "from transcriber import get_transcriber; t = get_transcriber(); t.load_model(); print('OK')"
```

### Updating

```bash
git pull origin main
# Restart the app - changes take effect immediately
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `mlx-whisper` | Apple Silicon optimized Whisper |
| `rumps` | macOS menu bar framework |
| `sounddevice` | Cross-platform audio I/O |
| `numpy` | Audio array processing |
| `scipy` | WAV file reading/writing |
| `pyobjc-framework-Cocoa` | AppKit/Foundation bindings |
| `pyobjc-framework-Quartz` | CGEventTap for keyboard |

---

## License

MIT License - feel free to modify and distribute.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Original speech recognition model
- [MLX](https://github.com/ml-explore/mlx) - Apple's machine learning framework
- [Wispr Flow](https://wispr.ai/) - Inspiration for the UX
- [rumps](https://github.com/jaredks/rumps) - Python menu bar framework
