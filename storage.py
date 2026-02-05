"""Storage module for transcription history."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

# Store history in user's Application Support
APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "VoiceDictation"
APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = APP_SUPPORT_DIR / "history.json"


@dataclass
class TranscriptionEntry:
    """A single transcription entry."""
    id: str
    text: str
    timestamp: str
    duration_seconds: float
    audio_file: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TranscriptionEntry":
        return cls(**data)


class TranscriptionHistory:
    """Manages transcription history storage."""

    def __init__(self):
        self.entries: list[TranscriptionEntry] = []
        self._load()

    def _load(self):
        """Load history from disk."""
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r") as f:
                    data = json.load(f)
                    self.entries = [TranscriptionEntry.from_dict(e) for e in data]
            except Exception as e:
                print(f"Error loading history: {e}")
                self.entries = []

    def _save(self):
        """Save history to disk."""
        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump([e.to_dict() for e in self.entries], f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def add(self, text: str, duration_seconds: float, audio_file: Optional[str] = None) -> TranscriptionEntry:
        """Add a new transcription entry."""
        entry = TranscriptionEntry(
            id=datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
            text=text,
            timestamp=datetime.now().isoformat(),
            duration_seconds=duration_seconds,
            audio_file=audio_file,
        )
        self.entries.insert(0, entry)  # Most recent first

        # Keep only last 100 entries
        if len(self.entries) > 100:
            self.entries = self.entries[:100]

        self._save()
        return entry

    def get_all(self) -> list[TranscriptionEntry]:
        """Get all entries (most recent first)."""
        return self.entries

    def get_recent(self, count: int = 10) -> list[TranscriptionEntry]:
        """Get most recent entries."""
        return self.entries[:count]

    def clear(self):
        """Clear all history."""
        self.entries = []
        self._save()


# Singleton instance
_history: Optional[TranscriptionHistory] = None


def get_history() -> TranscriptionHistory:
    """Get or create the history singleton."""
    global _history
    if _history is None:
        _history = TranscriptionHistory()
    return _history
