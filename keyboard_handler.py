"""Keyboard handler with support for Fn key and configurable hotkeys."""

import threading
from typing import Callable, Optional
import Quartz
from AppKit import NSEvent
from Foundation import NSObject
import objc
import config


class CallbackDispatcher(NSObject):
    """Helper to dispatch callbacks to the main thread."""

    def initWithCallbacks_(self, callbacks):
        self = objc.super(CallbackDispatcher, self).init()
        if self:
            self.on_press = callbacks.get('on_press')
            self.on_release = callbacks.get('on_release')
        return self

    def dispatchPress_(self, _):
        """Called on main thread to trigger press callback."""
        if self.on_press:
            self.on_press()

    def dispatchRelease_(self, _):
        """Called on main thread to trigger release callback."""
        if self.on_release:
            self.on_release()


# Modifier flags
FLAG_FN = 0x800000  # NSEventModifierFlagFunction
FLAG_CMD = Quartz.kCGEventFlagMaskCommand
FLAG_SHIFT = Quartz.kCGEventFlagMaskShift
FLAG_OPT = Quartz.kCGEventFlagMaskAlternate
FLAG_CTRL = Quartz.kCGEventFlagMaskControl
FLAG_RIGHT_CMD = 0x10  # Right Command key flag (in device-dependent bits)


class HotkeyHandler:
    """Handles configurable hotkeys using Quartz event taps."""

    def __init__(self, on_press: Callable, on_release: Callable):
        self.on_press = on_press
        self.on_release = on_release
        self.is_active = False
        self._running = False
        self._tap = None
        self._loop_source = None
        self._thread = None

        # Create dispatcher for main thread callbacks
        self._dispatcher = CallbackDispatcher.alloc().initWithCallbacks_({
            'on_press': on_press,
            'on_release': on_release,
        })

        # Track modifier states
        self._fn_held = False
        self._cmd_held = False
        self._right_cmd_held = False
        self._shift_held = False
        self._opt_held = False
        self._ctrl_held = False
        self._space_held = False

    def _check_hotkey(self) -> bool:
        """Check if current hotkey combination is active."""
        hotkey = config.get_current_hotkey()

        if hotkey == "fn":
            return self._fn_held

        elif hotkey == "right_cmd":
            return self._right_cmd_held

        elif hotkey == "cmd_shift_space":
            return self._cmd_held and self._shift_held and self._space_held

        elif hotkey == "opt_space":
            return self._opt_held and self._space_held

        elif hotkey == "ctrl_space":
            return self._ctrl_held and self._space_held

        return False

    def _handle_event(self, proxy, event_type, event, refcon):
        """Handle keyboard events."""
        if event_type == Quartz.kCGEventFlagsChanged:
            # Modifier key changed
            flags = Quartz.CGEventGetFlags(event)
            keycode = Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGKeyboardEventKeycode
            )

            # Track Fn key (flag-based, no specific keycode)
            self._fn_held = bool(flags & FLAG_FN)

            # Track Command keys
            # Right Command is keycode 54, Left Command is 55
            if keycode == 54:  # Right Command
                self._right_cmd_held = bool(flags & FLAG_CMD)
            elif keycode == 55:  # Left Command
                pass  # We don't track left cmd separately

            self._cmd_held = bool(flags & FLAG_CMD)
            self._shift_held = bool(flags & FLAG_SHIFT)
            self._opt_held = bool(flags & FLAG_OPT)
            self._ctrl_held = bool(flags & FLAG_CTRL)

        elif event_type == Quartz.kCGEventKeyDown:
            keycode = Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGKeyboardEventKeycode
            )
            if keycode == 49:  # Space
                self._space_held = True

        elif event_type == Quartz.kCGEventKeyUp:
            keycode = Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGKeyboardEventKeycode
            )
            if keycode == 49:  # Space
                self._space_held = False

        # Check hotkey state
        hotkey_active = self._check_hotkey()

        if hotkey_active and not self.is_active:
            self.is_active = True
            # Dispatch to main thread
            self._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_(
                "dispatchPress:", None, False
            )
        elif not hotkey_active and self.is_active:
            self.is_active = False
            # Dispatch to main thread
            self._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_(
                "dispatchRelease:", None, False
            )

        return event

    def _event_callback(self, proxy, event_type, event, refcon):
        """C callback wrapper."""
        try:
            return self._handle_event(proxy, event_type, event, refcon)
        except Exception as e:
            print(f"Event callback error: {e}")
            return event

    def start(self):
        """Start listening for hotkeys."""
        if self._running:
            return

        self._running = True

        def run_loop():
            # Create event tap
            events = (
                Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged) |
                Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown) |
                Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp)
            )

            self._tap = Quartz.CGEventTapCreate(
                Quartz.kCGSessionEventTap,
                Quartz.kCGHeadInsertEventTap,
                Quartz.kCGEventTapOptionListenOnly,
                events,
                self._event_callback,
                None,
            )

            if not self._tap:
                print("Failed to create event tap. Grant Accessibility permissions.")
                self._running = False
                return

            # Add to run loop
            self._loop_source = Quartz.CFMachPortCreateRunLoopSource(
                None, self._tap, 0
            )
            Quartz.CFRunLoopAddSource(
                Quartz.CFRunLoopGetCurrent(),
                self._loop_source,
                Quartz.kCFRunLoopCommonModes,
            )
            Quartz.CGEventTapEnable(self._tap, True)

            print(f"Keyboard listener started (hotkey: {config.get_current_hotkey()})")

            # Run the loop
            while self._running:
                Quartz.CFRunLoopRunInMode(
                    Quartz.kCFRunLoopDefaultMode, 0.1, False
                )

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop listening for hotkeys."""
        self._running = False
        if self._tap:
            Quartz.CGEventTapEnable(self._tap, False)


def get_hotkey_display() -> str:
    """Get display text for current hotkey."""
    hotkey = config.get_current_hotkey()
    if hotkey in config.HOTKEY_PRESETS:
        return config.HOTKEY_PRESETS[hotkey][1]
    return "Unknown"


# Test if run directly
if __name__ == "__main__":
    import time

    def on_press():
        print(">>> RECORDING START")

    def on_release():
        print("<<< RECORDING STOP")

    print("Testing hotkey handler...")
    print(f"Current hotkey: {get_hotkey_display()}")
    print("Press the hotkey to test. Ctrl+C to exit.")

    handler = HotkeyHandler(on_press, on_release)
    handler.start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        handler.stop()
        print("\nDone")
