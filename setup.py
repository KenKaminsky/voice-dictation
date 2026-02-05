"""
Setup script to build Voice Dictation as a macOS app.

Usage:
    python setup.py py2app
"""

from setuptools import setup

APP = ['app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,  # Add icon.icns here if you have one
    'plist': {
        'CFBundleName': 'Voice Dictation',
        'CFBundleDisplayName': 'Voice Dictation',
        'CFBundleIdentifier': 'com.voicedictation.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,  # Menu bar app (no dock icon)
        'NSMicrophoneUsageDescription': 'Voice Dictation needs microphone access to record your voice.',
        'NSAppleEventsUsageDescription': 'Voice Dictation needs to paste text into other applications.',
    },
    'packages': [
        'rumps',
        'pynput',
        'sounddevice',
        'numpy',
        'scipy',
        'mlx',
        'mlx_whisper',
        'pyperclip',
        'huggingface_hub',
        'tokenizers',
        'tiktoken',
    ],
    'includes': [
        'config',
        'recorder',
        'transcriber',
        'paster',
        'storage',
    ],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
