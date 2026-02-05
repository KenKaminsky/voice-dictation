#!/bin/bash
# Launch Voice Dictation app

cd "$(dirname "$0")"
source venv/bin/activate
exec python app.py
