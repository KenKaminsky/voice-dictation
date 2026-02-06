# Interruption Handling & Development Setup

## Audio Interruption Handling

### CRITICAL PRINCIPLE

# NOTHING STOPS RECORDING EXCEPT THE USER

**No external event should EVER stop, pause, or interrupt a recording.**

This is absolute. Non-negotiable. The ONLY way recording stops is:
- User explicitly presses Stop
- Phone physically shuts down (battery dead, forced reboot)

Everything else - calls, notifications, alarms, other apps, system events - is **IGNORED**.

| Event | Traditional App Behavior | OUR Behavior |
|-------|-------------------------|--------------|
| Incoming call | Stop/pause recording | **IGNORE - keep recording** |
| Call answered | Stop recording | **IGNORE - keep recording** |
| Alarm | Pause recording | **IGNORE - keep recording** |
| Other app wants mic | Give up mic | **REFUSE - keep recording** |
| Audio focus lost | Stop recording | **IGNORE - keep recording** |
| Low battery | Warn and stop | **KEEP RECORDING until shutdown** |
| App backgrounded | Stop recording | **KEEP RECORDING** |

### If the phone can still power the microphone, we are recording.

The caller can hear silence. The alarm can be muted. Other apps can fail. We don't care. Recording is sacred.

---

## Complete Interruption Catalog

### Category 1: Phone Calls

# ALL INCOMING CALLS ARE BLOCKED DURING RECORDING

**Calls don't just fail to interrupt - they are actively REJECTED.**

| Interruption | Our Response | Caller Experience |
|--------------|--------------|-------------------|
| **Incoming cellular call** | **REJECT immediately** | Goes to voicemail / shows as missed |
| **Incoming WhatsApp call** | **REJECT immediately** | Shows as missed call |
| **Incoming Telegram call** | **REJECT immediately** | Shows as missed call |
| **Incoming Zoom/Meet call** | **REJECT immediately** | Shows as missed/declined |
| **Any VoIP call** | **REJECT immediately** | Shows as missed/declined |

**The phone doesn't ring. The call is rejected before it can interfere. Recording continues undisturbed.**

**Implementation: CallScreeningService (Android 10+)**

```kotlin
// AndroidManifest.xml
<service
    android:name=".service.RecordingCallScreener"
    android:permission="android.permission.BIND_SCREENING_SERVICE">
    <intent-filter>
        <action android:name="android.telecom.CallScreeningService" />
    </intent-filter>
</service>

// Also need user to set us as default Call Screening app
// Or use ANSWER_PHONE_CALLS permission for direct rejection
```

```kotlin
class RecordingCallScreener : CallScreeningService() {

    override fun onScreenCall(callDetails: Call.Details) {
        // Check if we're currently recording
        if (RecordingService.isRecording) {
            // REJECT the call immediately
            val response = CallResponse.Builder()
                .setDisallowCall(true)           // Block the call
                .setRejectCall(true)             // Reject it (goes to voicemail)
                .setSkipCallLog(false)           // Show in call log as missed
                .setSkipNotification(true)       // Don't show incoming call notification
                .setSilenceCall(true)            // No ringtone
                .build()

            respondToCall(callDetails, response)

            // Log for metadata
            RecordingService.addMetadataEvent(
                "call_blocked",
                mapOf("number" to callDetails.handle.toString())
            )

            Log.i("CallScreener", "Blocked incoming call during recording")
        } else {
            // Not recording - let call through normally
            val response = CallResponse.Builder()
                .setDisallowCall(false)
                .build()
            respondToCall(callDetails, response)
        }
    }
}
```

**Alternative: TelecomManager Reject (Android 9+)**

```kotlin
class CallRejecter : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == TelephonyManager.ACTION_PHONE_STATE_CHANGED) {
            val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE)

            if (state == TelephonyManager.EXTRA_STATE_RINGING && RecordingService.isRecording) {
                // Reject the call
                val telecomManager = context.getSystemService(Context.TELECOM_SERVICE) as TelecomManager

                if (ActivityCompat.checkSelfPermission(context, Manifest.permission.ANSWER_PHONE_CALLS)
                    == PackageManager.PERMISSION_GRANTED) {
                    telecomManager.endCall()  // Immediately end/reject the incoming call
                    Log.i("CallRejecter", "Rejected incoming call during recording")
                }
            }
        }
    }
}
```

**Required Permissions:**

```xml
<uses-permission android:name="android.permission.ANSWER_PHONE_CALLS" />
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
<uses-permission android:name="android.permission.READ_CALL_LOG" />
```

**For VoIP Apps (WhatsApp, Telegram, etc.):**

VoIP apps use audio focus - we simply REFUSE to give it up:

```kotlin
// When recording, we hold exclusive audio focus
// VoIP apps will fail to acquire mic and show "call failed" or similar

val focusRequest = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE)
    .setOnAudioFocusChangeListener { focusChange ->
        // IGNORE ALL FOCUS CHANGES
        Log.w("Recording", "Audio focus request DENIED to other app: $focusChange")
    }
    .setAcceptsDelayedFocusGain(false)
    .setWillPauseWhenDucked(false)
    .build()

audioManager.requestAudioFocus(focusRequest)
```

**User Notification:**

After recording ends, show notification:
> "2 calls were blocked during your recording"
> [View Details] [Call Back]
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

**CRITICAL: In ALL these tests, recording must NEVER stop. Not pause. Not interrupt. NEVER.**

| Test ID | Scenario | Expected Result | FAIL if |
|---------|----------|-----------------|---------|
| INT-01 | Start recording, receive phone call | Call REJECTED, caller goes to voicemail, recording continues | Phone rings or recording stops |
| INT-02 | Start recording, receive 5 phone calls | All 5 calls REJECTED, recording continues, notification shows "5 calls blocked" | Any call gets through |
| INT-03 | Start recording, receive WhatsApp call | Call REJECTED/fails, recording continues | Recording stops or pauses |
| INT-04 | Start recording, receive Telegram call | Call REJECTED/fails, recording continues | Recording stops or pauses |
| INT-05 | Start recording, alarm goes off for 1 minute | Recording continues through alarm | Recording stopped |
| INT-06 | Start recording, play music in Spotify | Spotify silenced OR muted, recording continues | Recording stopped |
| INT-07 | Start recording, press Home, open other apps | Recording continues | Recording stopped |
| INT-08 | Start recording, screen off for 30 minutes | Recording continues, all chunks saved | Any gap or stop |
| INT-09 | Start recording, plug/unplug headphones 5 times | Recording continues | Any gap |
| INT-10 | Start recording, connect/disconnect Bluetooth | Recording continues | Any gap |
| INT-11 | Start recording, swipe app away from recents | Recording continues via service | Recording stopped |
| INT-12 | Start recording, enter split-screen mode | Recording continues | Recording stopped |
| INT-13 | Start recording, receive 50 notifications rapidly | Recording continues | Any interruption |
| INT-14 | Start recording, trigger Google Assistant | Recording continues, Assistant may fail | Recording stopped |
| INT-15 | Start recording, another app tries to use mic | Other app fails, recording continues | Recording stopped |
| INT-16 | Start recording, open Camera app | Camera may fail to record, our recording continues | Recording stopped |
| INT-17 | Start recording, open another voice recorder | Other recorder fails, our recording continues | Recording stopped |
| INT-18 | Start recording, phone goes to 1% battery | Recording continues until actual shutdown | Recording stopped early |

### Force Stop & Crash Recovery Tests

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| REC-01 | Force stop app mid-recording | All chunks up to that point saved and recoverable |
| REC-02 | Kill process via ADB mid-recording | All chunks up to that point saved |
| REC-03 | Phone crashes/reboots mid-recording | All written chunks recoverable after boot |
| REC-04 | Pull battery (if possible) mid-recording | All written chunks recoverable |
| REC-05 | Storage fills up mid-recording | Error shown, but existing chunks preserved |

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
