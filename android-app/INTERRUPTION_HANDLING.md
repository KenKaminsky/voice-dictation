# Interruption Handling & Development Setup

## Audio Interruption Handling

### CRITICAL PRINCIPLE

**No external event should EVER stop or corrupt a recording.**

The recording must continue through ALL of the following. If the system forces audio interruption, we must:
1. Save all audio captured so far (immediately)
2. Resume recording the moment the interruption ends
3. Mark the gap in metadata for user awareness
4. NEVER lose a single sample that was captured

---

## Complete Interruption Catalog

### Category 1: Phone Calls

| Interruption | System Behavior | Our Response |
|--------------|-----------------|--------------|
| **Incoming cellular call** | System takes audio focus | Continue recording via secondary channel OR pause + auto-resume |
| **Outgoing cellular call** | System takes audio focus | Same as above |
| **Incoming WhatsApp call** | App requests audio focus | IGNORE their focus request, keep recording |
| **Incoming Telegram call** | App requests audio focus | IGNORE their focus request, keep recording |
| **Incoming Zoom/Meet call** | App requests audio focus | IGNORE their focus request, keep recording |
| **Any VoIP call** | App requests audio focus | IGNORE their focus request, keep recording |

**Implementation Strategy:**

```kotlin
// We request AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE and NEVER release it during recording
audioManager.requestAudioFocus(
    focusRequest = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE)
        .setOnAudioFocusChangeListener { focusChange ->
            // IGNORE all focus changes during recording
            // Log for debugging but DO NOT stop recording
            Log.w("Recording", "Audio focus change ignored: $focusChange")
        }
        .setAcceptsDelayedFocusGain(false)
        .build()
)
```

**For Cellular Calls (Cannot Ignore):**

Android gives cellular calls priority over everything. Strategy:

1. **Detect incoming call** via `TelephonyManager.listen(LISTEN_CALL_STATE)`
2. **Before call connects**: Flush current chunk to disk immediately
3. **During call**:
   - Option A: Keep recording (call audio may bleed in - acceptable)
   - Option B: Pause recording, create gap marker
4. **After call ends**: Auto-resume recording seamlessly
5. **Metadata**: Mark the interruption with timestamps

```kotlin
class CallInterruptionHandler : PhoneStateListener() {
    override fun onCallStateChanged(state: Int, phoneNumber: String?) {
        when (state) {
            TelephonyManager.CALL_STATE_RINGING -> {
                // Incoming call - flush current audio immediately
                recordingService.flushCurrentChunk()
                recordingService.markInterruptionStart("incoming_call")
            }
            TelephonyManager.CALL_STATE_OFFHOOK -> {
                // Call answered - continue recording (captures both sides)
                // OR pause if user prefers privacy
            }
            TelephonyManager.CALL_STATE_IDLE -> {
                // Call ended - ensure recording continues
                recordingService.markInterruptionEnd()
                recordingService.ensureRecording()
            }
        }
    }
}
```

### Category 2: Notifications & Sounds

| Interruption | System Behavior | Our Response |
|--------------|-----------------|--------------|
| **Notification sound** | Brief audio | IGNORE - we have exclusive focus |
| **Alarm/Timer** | Loud, persistent | IGNORE - keep recording |
| **Media notification** | Brief audio | IGNORE - keep recording |
| **System sounds** | Brief audio | IGNORE - keep recording |
| **Ringtone (non-call)** | Audio playback | IGNORE - keep recording |

**All of these are handled by holding `AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE`.**

### Category 3: Other Apps

| Interruption | System Behavior | Our Response |
|--------------|-----------------|--------------|
| **Music app starts** | Requests audio focus | DENY - we have exclusive focus |
| **Video app starts** | Requests audio focus | DENY - we have exclusive focus |
| **Game with audio** | Requests audio focus | DENY - we have exclusive focus |
| **Voice assistant** | Requests mic + focus | DENY - we own the mic |
| **Camera app** | May request mic | Use FLAG to allow concurrent |

### Category 4: System State Changes

| Interruption | System Behavior | Our Response |
|--------------|-----------------|--------------|
| **Screen off** | May throttle apps | Foreground Service keeps us alive |
| **Doze mode** | Restricts background | Foreground Service exempt |
| **App Standby** | Limits background | Foreground Service exempt |
| **Battery Saver** | Restricts background | Foreground Service exempt |
| **Memory pressure** | Kills background apps | Foreground Service = high priority |
| **User force stops** | Kills app | Save chunk, notify user on reopen |
| **System reboot** | Everything stops | Chunk saved, resume on boot |

### Category 5: Audio Hardware Changes

| Interruption | System Behavior | Our Response |
|--------------|-----------------|--------------|
| **Headphones plugged in** | Audio route changes | Continue with new route |
| **Headphones unplugged** | Audio route changes | Continue with speaker mic |
| **Bluetooth connects** | Audio route changes | Continue with BT mic |
| **Bluetooth disconnects** | Audio route changes | Fall back to phone mic |
| **USB audio device** | Audio route changes | Continue with USB mic |

**Implementation:**

```kotlin
class AudioRouteReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            AudioManager.ACTION_HEADSET_PLUG,
            BluetoothAdapter.ACTION_CONNECTION_STATE_CHANGED -> {
                // Audio route changed - log it but DO NOT stop recording
                Log.i("Recording", "Audio route changed, continuing recording")
                // MediaRecorder/AudioRecord automatically handles route changes
            }
        }
    }
}
```

### Category 6: App Lifecycle

| Interruption | System Behavior | Our Response |
|--------------|-----------------|--------------|
| **User presses Home** | App goes to background | Foreground Service continues |
| **User presses Back** | Activity may finish | Foreground Service continues |
| **User opens other app** | Our app backgrounded | Foreground Service continues |
| **Split screen entered** | App resized | Continue recording |
| **Picture-in-picture** | App minimized | Continue recording |
| **User switches user** | Profile change | Save chunk, new user can't access |

---

## Foreground Service Configuration

The **key** to surviving all interruptions is proper Foreground Service setup:

```kotlin
class RecordingService : Service() {

    override fun onCreate() {
        super.onCreate()

        // Create notification channel (required Android 8+)
        createNotificationChannel()

        // Start as foreground IMMEDIATELY
        startForeground(NOTIFICATION_ID, createNotification())
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Recording",
            NotificationManager.IMPORTANCE_LOW  // Low = no sound, but visible
        ).apply {
            description = "Voice recording in progress"
            setShowBadge(false)
            lockscreenVisibility = Notification.VISIBILITY_PUBLIC
        }
        notificationManager.createNotificationChannel(channel)
    }

    private fun createNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Recording in progress")
            .setContentText("Tap to open app")
            .setSmallIcon(R.drawable.ic_mic)
            .setOngoing(true)  // Cannot be swiped away
            .setCategory(Notification.CATEGORY_SERVICE)
            .setForegroundServiceBehavior(FOREGROUND_SERVICE_IMMEDIATE)
            .addAction(stopAction)  // Quick stop button
            .build()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // START_STICKY = restart if killed
        return START_STICKY
    }
}
```

### AndroidManifest.xml Configuration

```xml
<manifest>
    <!-- Permissions -->
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    <uses-permission android:name="android.permission.READ_PHONE_STATE" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />

    <!-- Prevent battery optimization killing us -->
    <uses-permission android:name="android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS" />

    <application>
        <!-- Recording Service -->
        <service
            android:name=".service.RecordingService"
            android:enabled="true"
            android:exported="false"
            android:foregroundServiceType="microphone"
            android:stopWithTask="false">  <!-- Don't stop when app swiped away -->
        </service>

        <!-- Boot receiver to restart service -->
        <receiver
            android:name=".receiver.BootReceiver"
            android:enabled="true"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
                <action android:name="android.intent.action.QUICKBOOT_POWERON" />
            </intent-filter>
        </receiver>
    </application>
</manifest>
```

---

## Interruption Metadata

When any interruption occurs, record it in the session metadata:

```json
{
  "session_id": "rec_20240206_143022",
  "interruptions": [
    {
      "type": "phone_call",
      "started_at": "2024-02-06T14:32:15.000Z",
      "ended_at": "2024-02-06T14:33:42.000Z",
      "duration_seconds": 87,
      "audio_during_interruption": true,
      "chunk_at_start": "chunk_004.wav",
      "chunk_at_end": "chunk_006.wav"
    }
  ]
}
```

---

## Testing Interruption Handling

### Test Cases (Must Pass All)

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| INT-01 | Start recording, receive phone call, answer, hang up | Recording continues with metadata marker |
| INT-02 | Start recording, receive WhatsApp call, decline | Recording never interrupted |
| INT-03 | Start recording, alarm goes off | Recording continues |
| INT-04 | Start recording, play music in Spotify | Spotify silenced, recording continues |
| INT-05 | Start recording, press Home, open other apps | Recording continues |
| INT-06 | Start recording, screen off for 10 minutes | Recording continues |
| INT-07 | Start recording, plug/unplug headphones | Recording continues |
| INT-08 | Start recording, connect/disconnect Bluetooth | Recording continues |
| INT-09 | Start recording, reboot phone | Chunk saved, can recover |
| INT-10 | Start recording, battery dies | Chunks saved, can recover |
| INT-11 | Start recording, swipe app away | Recording continues |
| INT-12 | Start recording, force stop app | Current chunk saved |
| INT-13 | Start recording, enter split-screen | Recording continues |
| INT-14 | Start recording, receive 50 notifications | Recording continues |
| INT-15 | Start recording, Google Assistant triggered | Recording continues |

---

## Development & Testing Setup

### Option 1: Android Emulator (Recommended for Development)

**Works great on M4 Max** - Android emulator runs ARM images natively.

#### Setup

1. **Install Android Studio**
   ```bash
   brew install --cask android-studio
   ```

2. **Create ARM64 Emulator**
   - Open Android Studio → Tools → Device Manager
   - Create Virtual Device
   - Select: Pixel 7 Pro (or any)
   - Select System Image: **ARM64** (NOT x86)
     - API 34 (Android 14)
     - Target: Google APIs (for Play Services)
   - Finish

3. **Emulator Features for Testing**
   ```bash
   # Simulate incoming call
   adb emu gsm call 5551234567

   # End call
   adb emu gsm cancel 5551234567

   # Send SMS
   adb emu sms send 5551234567 "Test message"

   # Set battery level
   adb emu power capacity 15

   # Simulate network conditions
   adb emu network delay gprs
   adb emu network speed gsm
   ```

4. **Fast Deployment**
   ```bash
   # Build and install (from project root)
   ./gradlew installDebug

   # Or use Android Studio's Run button (Shift+F10)
   ```

#### Emulator Limitations

| Feature | Emulator Support |
|---------|-----------------|
| Microphone | ✓ Uses Mac microphone |
| Phone calls | ✓ Simulated via adb |
| Notifications | ✓ Full support |
| Background | ✓ Full support |
| Volume buttons | ✓ On-screen or keyboard |
| Bluetooth | ✗ Not supported |
| Real audio routing | ✗ Limited |

### Option 2: Scrcpy (Mirror Real Device)

Best for testing on actual hardware without constant reconnection.

```bash
# Install
brew install scrcpy

# Run (phone connected via USB, USB debugging enabled)
scrcpy

# With options
scrcpy --max-size 1024 --bit-rate 2M --max-fps 30
```

**Features:**
- See phone screen on Mac
- Control with mouse/keyboard
- Very low latency
- Works while testing real audio

### Option 3: Wireless ADB

Test on real device wirelessly:

```bash
# Initial setup (phone connected via USB)
adb tcpip 5555

# Get phone IP from Settings → About → IP Address
adb connect 192.168.1.xxx:5555

# Now disconnect USB, deploy wirelessly
./gradlew installDebug
```

### Option 4: Firebase Test Lab

For automated testing on real devices:

```yaml
# .github/workflows/test.yml
- uses: google-github-actions/firebase-test-lab@v1
  with:
    projectId: your-project
    model: oriole  # Pixel 6
    version: 33
    testType: instrumentation
```

---

## Development Workflow

### Recommended Setup

```
┌─────────────────────────────────────────────────────────────┐
│                    Development Setup                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Mac (M4 Max)                                              │
│   ├── Android Studio                                        │
│   │   └── ARM64 Emulator (API 34)                          │
│   │       ├── Test audio recording                          │
│   │       ├── Test interruptions (adb emu)                  │
│   │       └── Fast iteration                                │
│   │                                                          │
│   ├── Scrcpy (when testing on real phone)                  │
│   │   └── Mirror S24 Ultra screen                          │
│   │                                                          │
│   └── Voice Dictation Server                                │
│       └── Same machine, Tailscale loopback                  │
│                                                              │
│   Galaxy S24 Ultra (for final testing)                      │
│   ├── USB debugging enabled                                 │
│   ├── Install via wireless ADB                              │
│   └── Test real-world scenarios                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Iteration Cycle

1. **Write code** in Android Studio
2. **Run on emulator** (instant hot reload for UI)
3. **Test interruptions** with `adb emu` commands
4. **Weekly**: Test on real S24 Ultra
5. **Before release**: Full test suite on real device

### Debugging Tools

```bash
# View logs in real-time
adb logcat | grep -E "(Recording|AudioFocus|Chunk)"

# View app-specific logs
adb logcat --pid=$(adb shell pidof -s com.yourpackage)

# Dump audio state
adb shell dumpsys audio

# Check battery optimization
adb shell dumpsys deviceidle

# Force stop to test recovery
adb shell am force-stop com.yourpackage

# Simulate low memory
adb shell am memory-pressure critical
```

### Testing Checklist

```markdown
## Pre-Release Testing (Real Device)

### Recording Basics
- [ ] Start recording via volume button (screen off)
- [ ] Start recording via volume button (screen on)
- [ ] Start recording via floating bubble
- [ ] Stop recording
- [ ] 1-minute recording saves correctly
- [ ] 30-minute recording saves correctly
- [ ] 2-hour recording saves correctly

### Interruptions
- [ ] Incoming phone call (answer + hang up)
- [ ] Incoming phone call (decline)
- [ ] Incoming WhatsApp call
- [ ] Playing Spotify during recording
- [ ] Alarm goes off
- [ ] 20 notifications in a row
- [ ] Screen off for 30 minutes
- [ ] Open camera app
- [ ] Open voice recorder app
- [ ] Google Assistant activation

### Stress Tests
- [ ] Record for 4 hours continuously
- [ ] Record → call → hang up → repeat 10x
- [ ] Record with 10% battery
- [ ] Record with 95% storage full
- [ ] Pull battery during recording (if possible)
- [ ] Force reboot during recording

### Sync
- [ ] Upload over WiFi
- [ ] Upload over Tailscale
- [ ] Upload after offline recording
- [ ] Retry after server unavailable
```

---

## Samsung-Specific Considerations

### Galaxy S24 Ultra Optimizations

1. **Disable Battery Optimization**
   ```kotlin
   // Request user to disable battery optimization
   val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
       data = Uri.parse("package:$packageName")
   }
   startActivity(intent)
   ```

2. **Samsung Game Booster**
   - Can throttle apps
   - Add our app to "Game Booster" whitelist
   - Or detect and warn user

3. **Samsung Device Care**
   - "Sleeping apps" can kill background apps
   - Guide user to add us to "Never sleeping apps"

4. **One UI Specific**
   ```kotlin
   // Detect Samsung One UI
   val isOneUI = Build.MANUFACTURER.equals("samsung", ignoreCase = true)
   if (isOneUI) {
       // Show Samsung-specific setup guide
   }
   ```

---

*Document Version: 1.0*
*Last Updated: 2024-02-06*
