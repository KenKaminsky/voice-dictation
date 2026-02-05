"""Floating recording indicator - small, smooth, Wispr-like."""

import numpy as np
import objc
from Foundation import NSObject
from AppKit import (
    NSWindow,
    NSView,
    NSColor,
    NSBezierPath,
    NSFont,
    NSMutableParagraphStyle,
    NSCenterTextAlignment,
    NSFloatingWindowLevel,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSScreen,
    NSMakeRect,
    NSAttributedString,
    NSForegroundColorAttributeName,
    NSFontAttributeName,
    NSParagraphStyleAttributeName,
    NSEvent,
)
import threading
import time
from collections import deque


class WaveformView(NSView):
    """Custom view that draws a smooth audio waveform."""

    def initWithFrame_(self, frame):
        self = objc.super(WaveformView, self).initWithFrame_(frame)
        if self:
            # Smooth waveform with 20 bars
            self.num_bars = 20
            self.waveform_data = deque([0.1] * self.num_bars, maxlen=self.num_bars)
            self.target_data = [0.1] * self.num_bars
            self.status_text = "Recording"
            self.is_processing = False
            # Animation smoothing
            self._smoothing = 0.3  # Lower = smoother
        return self

    def updateWaveform_(self, raw_data):
        """Update waveform with smoothed data."""
        if raw_data is None or len(raw_data) == 0:
            return

        # Resample to num_bars points
        chunk_size = len(raw_data) // self.num_bars
        if chunk_size == 0:
            return

        new_values = []
        for i in range(self.num_bars):
            start = i * chunk_size
            end = start + chunk_size
            # RMS for smoother visualization
            chunk = raw_data[start:end]
            rms = np.sqrt(np.mean(chunk ** 2))
            new_values.append(rms)

        # Normalize
        max_val = max(new_values) if max(new_values) > 0 else 1
        new_values = [v / max_val for v in new_values]

        # Smooth transition
        for i in range(self.num_bars):
            current = list(self.waveform_data)[i]
            target = new_values[i]
            # Exponential smoothing
            smoothed = current + self._smoothing * (target - current)
            self.waveform_data[i] = max(0.08, min(1.0, smoothed))

        self.setNeedsDisplay_(True)

    def setStatusText_(self, text):
        """Update status text."""
        self.status_text = text
        self.setNeedsDisplay_(True)

    def setProcessing_(self, processing):
        """Set processing state."""
        self.is_processing = processing
        if processing:
            # Reset to flat bars for processing animation
            for i in range(self.num_bars):
                self.waveform_data[i] = 0.3
        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):
        """Draw the waveform and status."""
        bounds = self.bounds()
        width = bounds.size.width
        height = bounds.size.height

        # Draw rounded pill background (dark)
        bg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            bounds, height / 2, height / 2
        )
        NSColor.colorWithRed_green_blue_alpha_(0.1, 0.1, 0.1, 0.95).setFill()
        bg_path.fill()

        # Waveform area
        waveform_width = width - 80  # Leave space for text
        bar_width = 3
        bar_spacing = (waveform_width - (self.num_bars * bar_width)) / (self.num_bars - 1)
        start_x = 12
        max_bar_height = height - 16

        # Color based on state
        if self.is_processing:
            NSColor.colorWithRed_green_blue_alpha_(0.4, 0.6, 1.0, 1.0).setFill()
        else:
            NSColor.colorWithRed_green_blue_alpha_(1.0, 0.5, 0.3, 1.0).setFill()

        # Draw waveform bars (centered vertically)
        for i, amplitude in enumerate(self.waveform_data):
            x = start_x + i * (bar_width + bar_spacing)
            bar_height = max(4, amplitude * max_bar_height * 0.7)
            y = (height - bar_height) / 2

            bar_rect = NSMakeRect(x, y, bar_width, bar_height)
            bar_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                bar_rect, bar_width / 2, bar_width / 2
            )
            bar_path.fill()

        # Draw status text on right side
        paragraph_style = NSMutableParagraphStyle.alloc().init()
        paragraph_style.setAlignment_(NSCenterTextAlignment)

        attrs = {
            NSForegroundColorAttributeName: NSColor.colorWithRed_green_blue_alpha_(0.7, 0.7, 0.7, 1.0),
            NSFontAttributeName: NSFont.systemFontOfSize_weight_(11, 0.3),
            NSParagraphStyleAttributeName: paragraph_style,
        }

        text = NSAttributedString.alloc().initWithString_attributes_(
            self.status_text, attrs
        )
        text_rect = NSMakeRect(width - 70, (height - 14) / 2, 60, 14)
        text.drawInRect_(text_rect)


class IndicatorController(NSObject):
    """Controller that handles main thread operations."""

    def init(self):
        self = objc.super(IndicatorController, self).init()
        if self:
            self.window = None
            self.waveform_view = None
            self._is_visible = False
            self._should_animate = False
            # Window dimensions - small pill shape
            self.window_width = 180
            self.window_height = 36
        return self

    def getActiveScreen(self):
        """Get the screen where the mouse cursor is located."""
        mouse_location = NSEvent.mouseLocation()
        for screen in NSScreen.screens():
            frame = screen.frame()
            if (frame.origin.x <= mouse_location.x <= frame.origin.x + frame.size.width and
                frame.origin.y <= mouse_location.y <= frame.origin.y + frame.size.height):
                return screen
        return NSScreen.mainScreen()

    def createWindow(self):
        """Create the floating window on main thread."""
        if self.window is not None:
            return

        # Get active screen
        screen = self.getActiveScreen()
        screen_frame = screen.frame()

        # Position at bottom center of active screen
        x = screen_frame.origin.x + (screen_frame.size.width - self.window_width) / 2
        y = screen_frame.origin.y + 80  # 80 points from bottom

        frame = NSMakeRect(x, y, self.window_width, self.window_height)

        # Create borderless, floating window
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )

        self.window.setLevel_(NSFloatingWindowLevel)
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(NSColor.clearColor())
        self.window.setHasShadow_(True)
        self.window.setIgnoresMouseEvents_(True)
        self.window.setCollectionBehavior_(1 << 1)  # NSWindowCollectionBehaviorCanJoinAllSpaces

        # Create waveform view
        content_frame = NSMakeRect(0, 0, self.window_width, self.window_height)
        self.waveform_view = WaveformView.alloc().initWithFrame_(content_frame)
        self.window.setContentView_(self.waveform_view)

    def repositionWindow(self):
        """Reposition window to active screen."""
        if self.window is None:
            return

        screen = self.getActiveScreen()
        screen_frame = screen.frame()

        x = screen_frame.origin.x + (screen_frame.size.width - self.window_width) / 2
        y = screen_frame.origin.y + 80

        self.window.setFrameOrigin_((x, y))

    def showRecording_(self, _):
        """Show recording state."""
        self.createWindow()
        self.repositionWindow()
        self.waveform_view.setStatusText_("REC")
        self.waveform_view.setProcessing_(False)
        self.window.orderFront_(None)
        self._is_visible = True
        self._should_animate = True

    def showProcessing_(self, _):
        """Show processing state."""
        if self.window and self.waveform_view:
            self._should_animate = False
            self.waveform_view.setStatusText_("...")
            self.waveform_view.setProcessing_(True)
            # Start animation thread
            thread = threading.Thread(target=self._animate_processing, daemon=True)
            thread.start()

    def _animate_processing(self):
        """Animate processing state."""
        phase = 0
        while self._is_visible and not self._should_animate:
            # Create a wave pattern for processing
            wave_data = []
            for i in range(20):
                # Sine wave animation
                val = 0.3 + 0.2 * np.sin((i + phase) * 0.5)
                wave_data.append(val)

            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "updateProcessingWave:", wave_data, False
            )
            phase += 1
            time.sleep(0.05)

    def updateProcessingWave_(self, wave_data):
        """Update processing wave animation."""
        if self.waveform_view and self._is_visible:
            for i, val in enumerate(wave_data):
                if i < len(self.waveform_view.waveform_data):
                    self.waveform_view.waveform_data[i] = val
            self.waveform_view.setNeedsDisplay_(True)

    def updateWaveform_(self, data):
        """Update waveform on main thread."""
        if self.waveform_view and self._is_visible:
            self.waveform_view.updateWaveform_(data)

    def hide_(self, _):
        """Hide the indicator on main thread."""
        self._should_animate = False
        self._is_visible = False
        if self.window:
            self.window.orderOut_(None)


class FloatingIndicator:
    """Floating window that shows recording status and waveform."""

    def __init__(self):
        self.controller = IndicatorController.alloc().init()
        self._is_visible = False

    def show_recording(self):
        """Show recording state with animation."""
        self._is_visible = True
        self.controller.performSelectorOnMainThread_withObject_waitUntilDone_(
            "showRecording:", None, False
        )

    def show_processing(self):
        """Show processing state."""
        self.controller.performSelectorOnMainThread_withObject_waitUntilDone_(
            "showProcessing:", None, False
        )

    def update_waveform(self, audio_chunk):
        """Update waveform with new audio data."""
        if self._is_visible:
            self.controller.performSelectorOnMainThread_withObject_waitUntilDone_(
                "updateWaveform:", audio_chunk, False
            )

    def hide(self):
        """Hide the indicator."""
        self._is_visible = False
        self.controller.performSelectorOnMainThread_withObject_waitUntilDone_(
            "hide:", None, False
        )


# Singleton instance
_indicator = None


def get_indicator() -> FloatingIndicator:
    """Get or create the indicator singleton."""
    global _indicator
    if _indicator is None:
        _indicator = FloatingIndicator()
    return _indicator
