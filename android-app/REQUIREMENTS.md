# Voice Dictation Android App - Requirements Document

## Project Overview

A voice recording and transcription app for Android that prioritizes **audio reliability above all else**. Records voice notes with one-touch activation (even from pocket), stores audio locally with fault-tolerant chunking, and transcribes via a self-hosted Mac server over Tailscale.

**Target Device**: Samsung Galaxy S24 Ultra
**Server**: macOS with MLX-Whisper (existing voice-dictation setup)
**Network**: Tailscale VPN for secure connectivity

---

## Core Principles

### 1. AUDIO MUST NEVER BE LOST

This is the **non-negotiable, fundamental requirement**. Every design decision must prioritize audio preservation.

| Scenario | Required Behavior |
|----------|------------------|
| App crashes during recording | Audio chunks already saved must be preserved |
| Phone dies mid-recording | All chunks up to that point must be recoverable |
| Storage full | Must warn BEFORE recording, never during |
| Network unavailable | Audio stored locally, synced later |
| Server unavailable | Audio stored locally, transcribed later |
| App killed by OS | Background service must continue recording |

### 2. Local-First Architecture

- All audio is written to local storage FIRST
- Network operations are secondary and can fail gracefully
- App must function fully offline
- Sync happens opportunistically when connected

### 3. Privacy & Security

- Audio never touches external cloud services
- Transcription only via self-hosted server over Tailscale
- All network traffic encrypted (Tailscale provides this)
- Local storage encrypted with Android Keystore

---

## Functional Requirements

### FR-1: Recording Activation

#### FR-1.1: Volume Button Trigger
- Long-press Volume Down (2+ seconds) starts recording
- Works when screen is off
- Works when phone is locked
- Works when phone is in pocket
- Haptic feedback confirms recording started

#### FR-1.2: Alternative Triggers
- Floating bubble (when screen is on)
- Quick Settings tile
- Lock screen shortcut
- Notification action (persistent notification when app active)

#### FR-1.3: Recording Stop
- Single press Volume Down stops recording
- Or: Long-press Volume Down again
- Or: Tap floating bubble
- Haptic feedback confirms recording stopped

### FR-2: Audio Recording

#### FR-2.1: Audio Format
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Format | WAV (PCM) | Lossless, no encoding overhead |
| Sample Rate | 16kHz | Whisper native format |
| Channels | Mono | Voice doesn't need stereo |
| Bit Depth | 16-bit | Standard quality |

#### FR-2.2: Chunked Storage (CRITICAL)

Audio must be saved in chunks to prevent data loss:

```
Recording Session: rec_20240206_143022
├── chunk_000.wav  (0:00 - 0:30)   ✓ saved
├── chunk_001.wav  (0:30 - 1:00)   ✓ saved
├── chunk_002.wav  (1:00 - 1:30)   ✓ saved
├── chunk_003.wav  (1:30 - 2:00)   ⏳ recording...
└── metadata.json
```

| Parameter | Value |
|-----------|-------|
| Chunk Duration | 30 seconds |
| Chunk Overlap | 0.5 seconds (for seamless stitching) |
| Write Strategy | Flush to disk every chunk |
| Buffer in Memory | Current chunk only |

#### FR-2.3: Storage Location
- Primary: App-specific external storage (`/Android/data/...`)
- Backup: Internal storage if external unavailable
- Never use cache directories (can be cleared by OS)

#### FR-2.4: Pre-Recording Checks
Before any recording starts:
1. Check available storage (require minimum 500MB free)
2. Verify write permissions
3. Test write to storage (create and delete test file)
4. If any check fails: Show error, DO NOT start recording

### FR-3: Recording Session Management

#### FR-3.1: Session Metadata
Each recording session stores:

```json
{
  "session_id": "rec_20240206_143022",
  "started_at": "2024-02-06T14:30:22.000Z",
  "ended_at": "2024-02-06T14:35:45.000Z",
  "duration_seconds": 323,
  "chunks": [
    {"file": "chunk_000.wav", "start": 0, "end": 30, "size_bytes": 960000},
    {"file": "chunk_001.wav", "start": 30, "end": 60, "size_bytes": 960000}
  ],
  "total_size_bytes": 10320000,
  "status": "pending_upload",
  "transcription": null,
  "sync_status": {
    "uploaded": false,
    "upload_attempts": 0,
    "last_attempt": null,
    "transcribed": false
  }
}
```

#### FR-3.2: Session States

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  RECORDING  │ ──▶ │   STORED    │ ──▶ │  UPLOADING  │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                    ┌─────────────┐           │
                    │   FAILED    │ ◀─────────┤ (retry)
                    └─────────────┘           │
                                              ▼
                    ┌─────────────┐     ┌─────────────┐
                    │ TRANSCRIBED │ ◀── │  UPLOADED   │
                    └─────────────┘     └─────────────┘
```

### FR-4: Sync & Upload

#### FR-4.1: Sync Conditions
Upload to server when ALL conditions met:
1. Recording is complete (not actively recording)
2. Tailscale VPN is connected
3. Server is reachable (health check passes)
4. WiFi connected OR user enabled "sync on cellular"

#### FR-4.2: Upload Process
1. Concatenate all chunks into single WAV file
2. Upload to Mac server via HTTP POST
3. Wait for server acknowledgment
4. Mark session as "uploaded"
5. Retain local copy (configurable retention period)

#### FR-4.3: Retry Logic
| Attempt | Delay |
|---------|-------|
| 1st retry | 1 minute |
| 2nd retry | 5 minutes |
| 3rd retry | 15 minutes |
| 4th+ retry | 1 hour |

After 24 hours of failures: Notify user

#### FR-4.4: Offline Queue
- All pending uploads queued persistently
- Queue survives app restart, phone restart
- Queue processed in FIFO order
- User can manually trigger sync

### FR-5: Transcription

#### FR-5.1: Transcription Modes

**Mode A: Real-time (< 5 minutes)**
- Audio streamed to server while recording
- Transcription returned within seconds of recording end
- Displayed immediately on phone

**Mode B: Batch (≥ 5 minutes)**
- Full audio uploaded after recording
- Server transcribes asynchronously
- Phone polls for completion or receives push notification
- Transcription stored locally when received

#### FR-5.2: Transcription Display
- Full text with timestamps
- Searchable
- Copy to clipboard
- Share as text
- Export options (TXT, JSON, SRT)

### FR-6: User Interface

#### FR-6.1: Main Screen
- List of all recordings (newest first)
- Each item shows:
  - Date/time
  - Duration
  - Sync status icon (✓ synced, ⏳ pending, ⚠️ failed)
  - Transcription status (✓ transcribed, ⏳ pending, — not requested)
  - First line of transcription (preview)

#### FR-6.2: Recording Screen
- Large, clear recording indicator
- Elapsed time
- Audio waveform visualization
- Pause/Resume button
- Stop button
- "Recording will be saved even if app closes" indicator

#### FR-6.3: Recording Detail Screen
- Full transcription text
- Audio player with seek
- Sync status with retry button
- Delete option (with confirmation)
- Share options

#### FR-6.4: Settings Screen
- Server URL configuration
- Tailscale status indicator
- Storage usage
- Sync on cellular toggle
- Audio quality settings
- Notification preferences
- Export all data option

#### FR-6.5: Status Indicators
Always visible when relevant:
- Recording indicator (in status bar)
- Sync status (pending count badge)
- Storage warning (if < 500MB free)
- Server connection status

### FR-7: Notifications

| Event | Notification Type |
|-------|------------------|
| Recording started | Ongoing (required for foreground service) |
| Recording stopped | Transient, shows duration |
| Upload complete | Transient |
| Transcription ready | Persistent until viewed |
| Upload failed (after retries) | Persistent, actionable |
| Low storage warning | Persistent |

### FR-8: Data Retention

#### FR-8.1: Local Retention
- Default: Keep all recordings forever
- Optional: Auto-delete after X days (user configurable)
- Never auto-delete un-synced recordings

#### FR-8.2: Server Retention
- Configured on server side
- Default: Keep forever
- Server stores both audio and transcription

---

## Non-Functional Requirements

### NFR-1: Reliability

| Metric | Target |
|--------|--------|
| Audio loss rate | 0% (ZERO tolerance) |
| Recording success rate | 99.9%+ |
| Chunk write latency | < 100ms |
| App crash during recording | Must not lose data |

### NFR-2: Performance

| Metric | Target |
|--------|--------|
| Time to start recording | < 500ms from button press |
| Memory usage during recording | < 50MB |
| Battery drain (recording) | < 5% per hour |
| Battery drain (idle) | < 1% per day |

### NFR-3: Storage

| Metric | Value |
|--------|-------|
| Audio size per minute | ~1.9MB (16kHz 16-bit mono WAV) |
| 1 hour recording | ~115MB |
| Minimum free space required | 500MB |
| Warning threshold | 1GB free |

### NFR-4: Security

- All local audio encrypted at rest (Android Keystore)
- All network traffic over Tailscale (WireGuard encryption)
- No analytics or telemetry
- No external dependencies that could exfiltrate data

### NFR-5: Compatibility

- Minimum Android version: 10 (API 29)
- Target Android version: 14 (API 34)
- Primary device: Samsung Galaxy S24 Ultra
- Should work on any Android 10+ device

---

## Technical Architecture

### Android App Components

```
┌────────────────────────────────────────────────────────────────┐
│                        Android App                              │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ VolumeButton    │  │ FloatingBubble  │  │ QuickSettings  │  │
│  │ Service         │  │ Service         │  │ Tile           │  │
│  └────────┬────────┘  └────────┬────────┘  └───────┬────────┘  │
│           │                    │                    │           │
│           ▼                    ▼                    ▼           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              RecordingForegroundService                   │  │
│  │  - Runs in foreground (survives app kill)                │  │
│  │  - Manages AudioRecord                                    │  │
│  │  - Writes chunks to storage                               │  │
│  │  - Shows ongoing notification                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    ChunkWriter                            │  │
│  │  - Manages 30-second chunks                               │  │
│  │  - Writes WAV headers                                     │  │
│  │  - Flushes to disk                                        │  │
│  │  - Updates metadata.json                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   RecordingRepository                     │  │
│  │  - Room database for session metadata                     │  │
│  │  - File management                                        │  │
│  │  - Query/search recordings                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    SyncWorker                             │  │
│  │  - WorkManager for reliable background sync               │  │
│  │  - Checks Tailscale connectivity                          │  │
│  │  - Uploads to Mac server                                  │  │
│  │  - Fetches transcriptions                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                              │
                              │ Tailscale VPN
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                     Mac Transcription Server                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Server                         │  │
│  │  POST /upload      - Receive audio                        │  │
│  │  GET  /status/{id} - Check transcription status           │  │
│  │  GET  /result/{id} - Get transcription                    │  │
│  │  GET  /health      - Health check                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              MLX-Whisper Transcriber                      │  │
│  │  - Same as existing voice-dictation app                   │  │
│  │  - large-v3-turbo model                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Storage                                │  │
│  │  - Audio files                                            │  │
│  │  - Transcription JSON                                     │  │
│  │  - SQLite database for metadata                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Key Android Components

| Component | Type | Purpose |
|-----------|------|---------|
| `RecordingService` | Foreground Service | Survives app termination |
| `VolumeButtonReceiver` | Accessibility Service | Captures hardware buttons |
| `ChunkWriter` | Utility | Reliable chunked audio storage |
| `RecordingDatabase` | Room DB | Metadata persistence |
| `SyncWorker` | WorkManager | Reliable background uploads |
| `TailscaleChecker` | Utility | VPN connectivity detection |

### Server API

#### POST /api/upload
```json
// Request
{
  "session_id": "rec_20240206_143022",
  "duration_seconds": 323,
  "recorded_at": "2024-02-06T14:30:22.000Z"
}
// + multipart file: audio.wav

// Response
{
  "status": "accepted",
  "job_id": "job_abc123",
  "estimated_seconds": 30
}
```

#### GET /api/status/{job_id}
```json
{
  "job_id": "job_abc123",
  "status": "completed",  // pending, processing, completed, failed
  "progress": 100
}
```

#### GET /api/result/{job_id}
```json
{
  "job_id": "job_abc123",
  "session_id": "rec_20240206_143022",
  "transcription": {
    "text": "Full transcription text here...",
    "segments": [
      {"start": 0.0, "end": 2.5, "text": "Hello..."},
      {"start": 2.5, "end": 5.0, "text": "This is..."}
    ],
    "language": "en",
    "duration": 323.5
  }
}
```

#### GET /api/health
```json
{
  "status": "healthy",
  "model_loaded": true,
  "pending_jobs": 2,
  "uptime_seconds": 86400
}
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Project setup (Kotlin, Gradle, dependencies)
- [ ] Basic UI scaffolding
- [ ] AudioRecord implementation
- [ ] Chunked WAV writer with reliability guarantees
- [ ] Local storage with Room database
- [ ] Basic recording list UI

### Phase 2: Recording Reliability (Week 3)
- [ ] Foreground service implementation
- [ ] Chunk overlap and stitching
- [ ] Crash recovery testing
- [ ] Storage checks and warnings
- [ ] Extensive failure mode testing

### Phase 3: Activation Methods (Week 4)
- [ ] Volume button accessibility service
- [ ] Floating bubble overlay
- [ ] Quick settings tile
- [ ] Lock screen shortcut
- [ ] Haptic feedback

### Phase 4: Server Integration (Week 5)
- [ ] Mac server implementation (FastAPI)
- [ ] Tailscale connectivity detection
- [ ] Upload implementation
- [ ] WorkManager sync scheduling
- [ ] Retry logic

### Phase 5: Transcription (Week 6)
- [ ] Server-side transcription queue
- [ ] Polling for results
- [ ] Transcription display UI
- [ ] Search functionality

### Phase 6: Polish (Week 7-8)
- [ ] UI/UX refinement
- [ ] Settings screen
- [ ] Export functionality
- [ ] Battery optimization
- [ ] Testing on multiple devices
- [ ] Documentation

---

## Risk Mitigation

### Risk: Audio Loss During Recording

**Mitigations:**
1. 30-second chunks written immediately to disk
2. Foreground service cannot be killed by OS
3. Chunks have 0.5s overlap for recovery
4. Pre-recording storage checks
5. Continuous monitoring of write success

### Risk: Server Unavailable

**Mitigations:**
1. Full offline functionality
2. Unlimited local storage queue
3. Automatic retry with backoff
4. Manual sync trigger option
5. Clear status indicators

### Risk: Phone Runs Out of Storage

**Mitigations:**
1. Pre-recording storage check (500MB minimum)
2. Warning at 1GB free
3. Clear storage usage display
4. Easy bulk delete of old synced recordings

### Risk: Tailscale Disconnected

**Mitigations:**
1. Explicit Tailscale status in app
2. Queue uploads for when connected
3. Don't attempt upload without VPN
4. Option to wait for WiFi only

---

## Success Criteria

### Must Have (MVP)
- [ ] One-tap recording start/stop
- [ ] 100% audio capture reliability
- [ ] Chunked storage with crash recovery
- [ ] Local playback of recordings
- [ ] Upload to Mac server over Tailscale
- [ ] View transcription on phone

### Should Have
- [ ] Volume button activation
- [ ] Real-time transcription for short recordings
- [ ] Search through transcriptions
- [ ] Export functionality

### Nice to Have
- [ ] Waveform visualization
- [ ] Edit transcription
- [ ] Tags/folders organization
- [ ] Widgets

---

## Open Questions

1. **Chunk size**: 30 seconds is proposed. Should we test 15s or 60s?
2. **Encryption**: Should local audio be encrypted? (Performance vs security)
3. **Compression**: Store as WAV or compress to FLAC/OPUS before upload?
4. **Real-time streaming**: Worth the complexity for <5min recordings?
5. **Multiple servers**: Support backup server if primary unavailable?

---

## Appendix

### A. Storage Calculations

| Recording Duration | WAV Size | With 100 recordings |
|-------------------|----------|---------------------|
| 1 minute | 1.9 MB | 190 MB |
| 5 minutes | 9.5 MB | 950 MB |
| 30 minutes | 57 MB | 5.7 GB |
| 1 hour | 114 MB | 11.4 GB |

S24 Ultra has 256GB-1TB storage, so this is manageable.

### B. Battery Estimates

| Activity | Power Draw | Per Hour |
|----------|------------|----------|
| Recording (screen off) | ~100mA | ~2% |
| Idle (service running) | ~5mA | ~0.1% |
| Upload (WiFi) | ~150mA | ~3% |
| Transcription display | ~200mA | ~4% |

### C. Permissions Required

| Permission | Purpose |
|------------|---------|
| `RECORD_AUDIO` | Microphone access |
| `FOREGROUND_SERVICE` | Keep recording alive |
| `POST_NOTIFICATIONS` | Status notifications |
| `RECEIVE_BOOT_COMPLETED` | Restart service on boot |
| `SYSTEM_ALERT_WINDOW` | Floating bubble |
| `BIND_ACCESSIBILITY_SERVICE` | Volume button capture |
| `INTERNET` | Server communication |
| `ACCESS_NETWORK_STATE` | Check connectivity |

---

*Document Version: 1.0*
*Last Updated: 2024-02-06*
*Author: Ken Kaminsky + Claude*
