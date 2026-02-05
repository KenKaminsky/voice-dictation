"""Floating recording indicator with waveform visualization."""

import numpy as np
import objc
from Foundation import NSObject
from AppKit import (
    NSApplication,
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
)
from PyObjCTools import AppHelper
import threading
import time


class WaveformView(NSView):
    """Custom view that draws audio waveform."""

    def initWithFrame_(self, frame):
        self = objc.super(WaveformView, self).initWithFrame_(frame)
        if self:
            self.waveform_data = np.zeros(50)
            self.status_text = "Recording..."
            self.is_processing = False
        return self

    def setWaveformData_(self, data):
        """Update waveform data and redraw."""
        if len(data) > 0:
            # Resample to 50 points for display
            indices = np.linspace(0, len(data) - 1, 50).astype(int)
            self.waveform_data = np.abs(data[indices])
            # Normalize
            max_val = np.max(self.waveform_data)
            if max_val > 0:
                self.waveform_data = self.waveform_data / max_val
        self.setNeedsDisplay_(True)

    def setStatusText_(self, text):
        """Update status text."""
        self.status_text = text
        self.setNeedsDisplay_(True)

    def setProcessing_(self, processing):
        """Set processing state."""
        self.is_processing = processing
        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):
        """Draw the waveform and status."""
        bounds = self.bounds()
        width = bounds.size.width
        height = bounds.size.height

        # Draw rounded background
        bg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            bounds, 16, 16
        )

        # Background color - orange when recording, blue when processing
        if self.is_processing:
            NSColor.colorWithRed_green_blue_alpha_(0.2, 0.4, 0.8, 0.95).setFill()
        else:
            NSColor.colorWithRed_green_blue_alpha_(0.9, 0.4, 0.2, 0.95).setFill()
        bg_path.fill()

        # Draw waveform
        bar_width = 4
        bar_spacing = 2
        num_bars = len(self.waveform_data)
        total_waveform_width = num_bars * (bar_width + bar_spacing)
        start_x = (width - total_waveform_width) / 2
        waveform_height = height - 40  # Leave space for text

        NSColor.whiteColor().setFill()

        for i, amplitude in enumerate(self.waveform_data):
            x = start_x + i * (bar_width + bar_spacing)
            bar_height = max(4, amplitude * waveform_height * 0.8)
            y = (waveform_height - bar_height) / 2 + 30

            bar_rect = NSMakeRect(x, y, bar_width, bar_height)
            bar_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                bar_rect, 2, 2
            )
            bar_path.fill()

        # Draw status text
        paragraph_style = NSMutableParagraphStyle.alloc().init()
        paragraph_style.setAlignment_(NSCenterTextAlignment)

        attrs = {
            NSForegroundColorAttributeName: NSColor.whiteColor(),
            NSFontAttributeName: NSFont.systemFontOfSize_weight_(13, 0.5),
            NSParagraphStyleAttributeName: paragraph_style,
        }

        text = NSAttributedString.alloc().initWithString_attributes_(
            self.status_text, attrs
        )
        text_rect = NSMakeRect(0, 8, width, 20)
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
            self._pending_waveform = None
        return self

    def createWindow(self):
        """Create the floating window on main thread."""
        if self.window is not None:
            return

        # Window size
        window_width = 320
        window_height = 80

        # Position at bottom center of main screen
        screen = NSScreen.mainScreen()
        screen_frame = screen.frame()
        x = (screen_frame.size.width - window_width) / 2
        y = 100  # 100 points from bottom

        frame = NSMakeRect(x, y, window_width, window_height)

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

        # Create waveform view
        content_frame = NSMakeRect(0, 0, window_width, window_height)
        self.waveform_view = WaveformView.alloc().initWithFrame_(content_frame)
        self.window.setContentView_(self.waveform_view)

    def showRecording_(self, _):
        """Show recording state."""
        self.createWindow()
        self.waveform_view.setStatusText_("Recording...")
        self.waveform_view.setProcessing_(False)
        self.window.orderFront_(None)
        self._is_visible = True
        self._should_animate = True

    def showProcessing_(self, _):
        """Show processing state."""
        if self.window and self.waveform_view:
            self._should_animate = False
            self.waveform_view.setStatusText_("Transcribing...")
            self.waveform_view.setProcessing_(True)
            # Start animation thread
            thread = threading.Thread(target=self._animate_processing, daemon=True)
            thread.start()

    def _animate_processing(self):
        """Animate processing dots in background."""
        dots = 0
        while self._is_visible and not self._should_animate:
            dots = (dots % 3) + 1
            text = "Transcribing" + "." * dots
            # Update on main thread
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "updateStatusText:", text, False
            )
            time.sleep(0.3)

    def updateStatusText_(self, text):
        """Update status text on main thread."""
        if self.waveform_view:
            self.waveform_view.setStatusText_(text)

    def updateWaveform_(self, data):
        """Update waveform on main thread."""
        if self.waveform_view and self._is_visible:
            self.waveform_view.setWaveformData_(data)

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
            # Convert to NSData-compatible format and update on main thread
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
