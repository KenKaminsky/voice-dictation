"""Native macOS history viewer using AppKit with SF Symbols."""

import objc
from Foundation import (
    NSObject,
    NSMakeRect,
    NSMutableAttributedString,
    NSRange,
    NSURL,
)
from AppKit import (
    NSApplication,
    NSWindow,
    NSView,
    NSScrollView,
    NSTextField,
    NSSearchField,
    NSButton,
    NSColor,
    NSFont,
    NSFontWeightMedium,
    NSFontWeightSemibold,
    NSBezierPath,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskResizable,
    NSBackingStoreBuffered,
    NSViewWidthSizable,
    NSViewHeightSizable,
    NSViewMinYMargin,
    NSLineBreakByWordWrapping,
    NSBezelStyleRounded,
    NSControlSizeSmall,
    NSControlSizeRegular,
    NSPasteboard,
    NSPasteboardTypeString,
    NSScreen,
    NSApp,
    NSApplicationActivationPolicyRegular,
    NSForegroundColorAttributeName,
    NSBackgroundColorAttributeName,
    NSFontAttributeName,
    NSSound,
    NSImage,
    NSImageSymbolConfiguration,
    NSFontWeightRegular,
)
import threading
import os
from datetime import datetime
from pathlib import Path
from storage import get_history


def relative_time(timestamp_str: str) -> str:
    """Convert ISO timestamp to friendly relative time."""
    try:
        dt = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
        diff = now - dt

        seconds = diff.total_seconds()
        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            mins = int(seconds / 60)
            return f"{mins} min{'s' if mins != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 172800:
            return "Yesterday"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days} days ago"
        else:
            return dt.strftime("%b %d, %Y")
    except:
        return timestamp_str[:10]


def full_datetime(timestamp_str: str) -> str:
    """Get full formatted date/time."""
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%A, %B %d, %Y at %I:%M %p")
    except:
        return timestamp_str


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def calculate_wpm(text: str, duration_seconds: float) -> int:
    """Calculate words per minute."""
    if duration_seconds <= 0:
        return 0
    words = count_words(text)
    minutes = duration_seconds / 60
    return int(words / minutes) if minutes > 0 else 0


def format_duration(seconds: float) -> str:
    """Format seconds into human readable duration."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        mins = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds / 3600)
        mins = int((seconds % 3600) / 60)
        return f"{hours}h {mins}m"


def get_sf_symbol(name: str, size: float = 13, weight: str = "regular") -> NSImage:
    """Get an SF Symbol image."""
    # Map weight strings to NSFontWeight values
    weights = {
        "ultralight": -0.8,
        "thin": -0.6,
        "light": -0.4,
        "regular": 0.0,
        "medium": 0.23,
        "semibold": 0.3,
        "bold": 0.4,
        "heavy": 0.56,
        "black": 0.62,
    }

    image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, None)
    if image:
        # Configure the symbol
        config = NSImageSymbolConfiguration.configurationWithPointSize_weight_(
            size, weights.get(weight, 0.0)
        )
        return image.imageWithSymbolConfiguration_(config)
    return None


class StatsView(NSView):
    """Stats header view showing usage statistics."""

    def initWithFrame_entries_(self, frame, entries):
        self = objc.super(StatsView, self).initWithFrame_(frame)
        if self:
            self._setup_stats(entries)
        return self

    def _setup_stats(self, entries):
        """Set up stats display."""
        # Calculate stats
        total_recordings = len(entries)
        total_words = sum(count_words(e.text) for e in entries)
        total_duration = sum(e.duration_seconds for e in entries)
        avg_wpm = int(total_words / (total_duration / 60)) if total_duration > 0 else 0

        width = self.bounds().size.width
        stat_width = (width - 40) / 4

        stats = [
            ("Recordings", str(total_recordings), "waveform"),
            ("Total Words", f"{total_words:,}", "text.word.spacing"),
            ("Recording Time", format_duration(total_duration), "clock"),
            ("Avg Speed", f"{avg_wpm} WPM", "speedometer"),
        ]

        x = 20
        for label, value, icon_name in stats:
            self._create_stat(x, label, value, icon_name, stat_width)
            x += stat_width

    def _create_stat(self, x, label, value, icon_name, width):
        """Create a single stat display."""
        # Icon
        icon_image = get_sf_symbol(icon_name, size=16, weight="medium")
        if icon_image:
            icon_view = NSButton.alloc().initWithFrame_(NSMakeRect(x, 28, 24, 24))
            icon_view.setImage_(icon_image)
            icon_view.setBordered_(False)
            icon_view.setEnabled_(False)
            icon_view.setContentTintColor_(NSColor.secondaryLabelColor())
            self.addSubview_(icon_view)

        # Value (large)
        value_label = NSTextField.alloc().initWithFrame_(NSMakeRect(x + 28, 28, width - 32, 22))
        value_label.setStringValue_(value)
        value_label.setBezeled_(False)
        value_label.setDrawsBackground_(False)
        value_label.setEditable_(False)
        value_label.setSelectable_(False)
        value_label.setFont_(NSFont.systemFontOfSize_weight_(16, NSFontWeightSemibold))
        value_label.setTextColor_(NSColor.labelColor())
        self.addSubview_(value_label)

        # Label (small)
        label_field = NSTextField.alloc().initWithFrame_(NSMakeRect(x + 28, 10, width - 32, 16))
        label_field.setStringValue_(label)
        label_field.setBezeled_(False)
        label_field.setDrawsBackground_(False)
        label_field.setEditable_(False)
        label_field.setSelectable_(False)
        label_field.setFont_(NSFont.systemFontOfSize_(11))
        label_field.setTextColor_(NSColor.secondaryLabelColor())
        self.addSubview_(label_field)

    def drawRect_(self, rect):
        """Draw background."""
        bounds = self.bounds()
        bg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(bounds, 10, 10)
        NSColor.controlBackgroundColor().setFill()
        bg_path.fill()


class EntryView(NSView):
    """A single history entry view."""

    def initWithEntry_width_searchQuery_(self, entry, width, search_query=""):
        frame = NSMakeRect(0, 0, width, 100)
        self = objc.super(EntryView, self).initWithFrame_(frame)
        if self:
            self.entry = entry
            self.search_query = search_query
            self.sound = None
            self._setup_ui(width)
        return self

    def _setup_ui(self, width):
        """Set up the entry UI."""
        # Calculate stats
        word_count = count_words(self.entry.text)
        wpm = calculate_wpm(self.entry.text, self.entry.duration_seconds)
        rel_time = relative_time(self.entry.timestamp)
        duration = f"{self.entry.duration_seconds:.1f}s"
        full_time = full_datetime(self.entry.timestamp)

        # Top row: relative time, duration, word count, WPM
        meta_text = f"{rel_time}  ·  {duration}  ·  {word_count} words  ·  {wpm} WPM"
        meta_label = NSTextField.alloc().initWithFrame_(NSMakeRect(16, 70, width - 100, 20))
        meta_label.setStringValue_(meta_text)
        meta_label.setBezeled_(False)
        meta_label.setDrawsBackground_(False)
        meta_label.setEditable_(False)
        meta_label.setSelectable_(False)
        meta_label.setFont_(NSFont.systemFontOfSize_(11))
        meta_label.setTextColor_(NSColor.secondaryLabelColor())
        meta_label.setToolTip_(full_time)  # Show full date on hover
        self.addSubview_(meta_label)

        # Buttons on the right
        button_x = width - 36
        button_y = 66

        # Play button (if audio file exists)
        if self.entry.audio_file and os.path.exists(self.entry.audio_file):
            play_icon = get_sf_symbol("play.fill", size=12, weight="medium")
            play_btn = NSButton.alloc().initWithFrame_(NSMakeRect(button_x, button_y, 28, 28))
            if play_icon:
                play_btn.setImage_(play_icon)
            play_btn.setBordered_(False)
            play_btn.setToolTip_("Play recording")
            play_btn.setTarget_(self)
            play_btn.setAction_(objc.selector(self.playAudio_, signature=b'v@:@'))
            self.addSubview_(play_btn)
            self.play_btn = play_btn
            button_x -= 32

        # Copy button with SF Symbol
        copy_icon = get_sf_symbol("doc.on.doc", size=12, weight="medium")
        copy_btn = NSButton.alloc().initWithFrame_(NSMakeRect(button_x, button_y, 28, 28))
        if copy_icon:
            copy_btn.setImage_(copy_icon)
        copy_btn.setBordered_(False)
        copy_btn.setToolTip_("Copy to clipboard")
        copy_btn.setTarget_(self)
        copy_btn.setAction_(objc.selector(self.copyText_, signature=b'v@:@'))
        self.addSubview_(copy_btn)
        self.copy_btn = copy_btn

        # Text label with search highlighting
        text_label = NSTextField.alloc().initWithFrame_(NSMakeRect(16, 12, width - 32, 50))
        text_label.setBezeled_(False)
        text_label.setDrawsBackground_(False)
        text_label.setEditable_(False)
        text_label.setSelectable_(True)
        text_label.setFont_(NSFont.systemFontOfSize_(13))
        text_label.setTextColor_(NSColor.labelColor())
        text_label.setLineBreakMode_(NSLineBreakByWordWrapping)
        text_label.setMaximumNumberOfLines_(2)

        # Apply search highlighting if query exists
        if self.search_query:
            attributed = self._highlight_text(self.entry.text, self.search_query)
            text_label.setAttributedStringValue_(attributed)
        else:
            text_label.setStringValue_(self.entry.text)

        self.addSubview_(text_label)

    def _highlight_text(self, text, query):
        """Create attributed string with highlighted search matches."""
        attributed = NSMutableAttributedString.alloc().initWithString_(text)

        # Set base attributes
        full_range = NSRange(0, len(text))
        attributed.addAttribute_value_range_(
            NSFontAttributeName,
            NSFont.systemFontOfSize_(13),
            full_range
        )
        attributed.addAttribute_value_range_(
            NSForegroundColorAttributeName,
            NSColor.labelColor(),
            full_range
        )

        # Highlight matches (case-insensitive)
        query_lower = query.lower()
        text_lower = text.lower()
        start = 0

        while True:
            pos = text_lower.find(query_lower, start)
            if pos == -1:
                break

            match_range = NSRange(pos, len(query))
            # Yellow highlight background
            attributed.addAttribute_value_range_(
                NSBackgroundColorAttributeName,
                NSColor.systemYellowColor(),
                match_range
            )
            # Dark text for contrast
            attributed.addAttribute_value_range_(
                NSForegroundColorAttributeName,
                NSColor.blackColor(),
                match_range
            )
            start = pos + len(query)

        return attributed

    def copyText_(self, sender):
        """Copy text to clipboard."""
        pasteboard = NSPasteboard.generalPasteboard()
        pasteboard.clearContents()
        pasteboard.setString_forType_(self.entry.text, NSPasteboardTypeString)

        # Visual feedback - show checkmark
        check_icon = get_sf_symbol("checkmark", size=12, weight="bold")
        if check_icon:
            sender.setImage_(check_icon)
            sender.setContentTintColor_(NSColor.systemGreenColor())

        def reset():
            import time
            time.sleep(1.0)
            copy_icon = get_sf_symbol("doc.on.doc", size=12, weight="medium")
            if copy_icon:
                sender.setImage_(copy_icon)
                sender.setContentTintColor_(None)
        threading.Thread(target=reset, daemon=True).start()

    def playAudio_(self, sender):
        """Play the audio file."""
        if not self.entry.audio_file or not os.path.exists(self.entry.audio_file):
            return

        # Stop any currently playing sound
        if self.sound and self.sound.isPlaying():
            self.sound.stop()
            play_icon = get_sf_symbol("play.fill", size=12, weight="medium")
            if play_icon:
                sender.setImage_(play_icon)
            return

        # Play the audio
        url = NSURL.fileURLWithPath_(self.entry.audio_file)
        self.sound = NSSound.alloc().initWithContentsOfURL_byReference_(url, True)
        if self.sound:
            pause_icon = get_sf_symbol("pause.fill", size=12, weight="medium")
            if pause_icon:
                sender.setImage_(pause_icon)
            self.sound.play()

            # Reset button when done
            def check_done():
                import time
                while self.sound and self.sound.isPlaying():
                    time.sleep(0.2)
                play_icon = get_sf_symbol("play.fill", size=12, weight="medium")
                if play_icon:
                    sender.setImage_(play_icon)
            threading.Thread(target=check_done, daemon=True).start()

    def drawRect_(self, rect):
        """Draw background."""
        bounds = self.bounds()
        bg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(bounds, 10, 10)
        NSColor.controlBackgroundColor().setFill()
        bg_path.fill()


class HistoryContentView(NSView):
    """Scrollable content view containing all entries."""

    def initWithFrame_(self, frame):
        self = objc.super(HistoryContentView, self).initWithFrame_(frame)
        if self:
            self.entry_views = []
            self.all_entries = []
            self.filtered_entries = []
            self.search_query = ""
        return self

    def isFlipped(self):
        """Use flipped coordinates (origin at top-left)."""
        return True

    def loadEntries_(self, entries):
        """Load and display entries."""
        self.all_entries = entries
        self.filtered_entries = entries
        self._rebuild_views()

    def filterWithQuery_(self, query):
        """Filter entries by search query."""
        self.search_query = query.strip()
        query_lower = self.search_query.lower()
        if not query_lower:
            self.filtered_entries = self.all_entries
        else:
            self.filtered_entries = [
                e for e in self.all_entries
                if query_lower in e.text.lower()
            ]
        self._rebuild_views()

    def _rebuild_views(self):
        """Rebuild entry views."""
        # Remove old views
        for view in self.entry_views:
            view.removeFromSuperview()
        self.entry_views = []

        # Calculate dimensions
        width = self.bounds().size.width
        entry_height = 100
        spacing = 12
        padding_top = 8

        # Create entry views (top to bottom since flipped)
        y = padding_top
        for entry in self.filtered_entries:
            entry_view = EntryView.alloc().initWithEntry_width_searchQuery_(
                entry, width - 16, self.search_query
            )
            entry_view.setFrameOrigin_((8, y))
            self.addSubview_(entry_view)
            self.entry_views.append(entry_view)
            y += entry_height + spacing

        # Update content size
        total_height = max(
            y + padding_top,
            self.superview().bounds().size.height if self.superview() else 400
        )
        self.setFrameSize_((width, total_height))

    def resizeWithOldSuperviewSize_(self, oldSize):
        """Handle resize."""
        objc.super(HistoryContentView, self).resizeWithOldSuperviewSize_(oldSize)
        self._rebuild_views()


class HistoryWindowDelegate(NSObject):
    """Window delegate to handle window events."""

    def windowWillClose_(self, notification):
        """Stop the app when window closes."""
        NSApp.terminate_(None)


class HistoryViewerApp(NSObject):
    """Main history viewer application."""

    def init(self):
        self = objc.super(HistoryViewerApp, self).init()
        if self:
            self.window = None
            self.content_view = None
            self.search_field = None
            self.count_label = None
            self.stats_view = None
        return self

    def createWindow(self):
        """Create and show the history window."""
        # Get screen center
        screen = NSScreen.mainScreen()
        screen_frame = screen.visibleFrame()

        # Window size
        win_width = 720
        win_height = 640
        x = screen_frame.origin.x + (screen_frame.size.width - win_width) / 2
        y = screen_frame.origin.y + (screen_frame.size.height - win_height) / 2

        frame = NSMakeRect(x, y, win_width, win_height)

        # Create window
        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskResizable
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, style, NSBackingStoreBuffered, False
        )
        self.window.setTitle_("Transcription History")
        self.window.setMinSize_((540, 450))

        # Set delegate for close handling
        delegate = HistoryWindowDelegate.alloc().init()
        self.window.setDelegate_(delegate)
        self._delegate = delegate

        # Load entries first (needed for stats)
        history = get_history()
        entries = history.get_all()

        # Main container view
        container = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, win_width, win_height))
        container.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)

        # Stats view at top
        stats_frame = NSMakeRect(16, win_height - 80, win_width - 32, 64)
        self.stats_view = StatsView.alloc().initWithFrame_entries_(stats_frame, entries)
        self.stats_view.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        container.addSubview_(self.stats_view)

        # Search field below stats
        self.search_field = NSSearchField.alloc().initWithFrame_(
            NSMakeRect(16, win_height - 120, win_width - 32, 32)
        )
        self.search_field.setPlaceholderString_("Search transcriptions...")
        self.search_field.setFont_(NSFont.systemFontOfSize_(14))
        self.search_field.setTarget_(self)
        self.search_field.setAction_(objc.selector(self.searchChanged_, signature=b'v@:@'))
        self.search_field.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        container.addSubview_(self.search_field)

        # Count label
        self.count_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(16, win_height - 146, win_width - 32, 20)
        )
        self.count_label.setBezeled_(False)
        self.count_label.setDrawsBackground_(False)
        self.count_label.setEditable_(False)
        self.count_label.setSelectable_(False)
        self.count_label.setFont_(NSFont.systemFontOfSize_(12))
        self.count_label.setTextColor_(NSColor.secondaryLabelColor())
        self.count_label.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        container.addSubview_(self.count_label)

        # Scroll view for entries
        scroll_frame = NSMakeRect(8, 8, win_width - 16, win_height - 162)
        scroll_view = NSScrollView.alloc().initWithFrame_(scroll_frame)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutohidesScrollers_(True)
        scroll_view.setBorderType_(0)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setDrawsBackground_(False)

        # Content view inside scroll view
        self.content_view = HistoryContentView.alloc().initWithFrame_(
            NSMakeRect(0, 0, scroll_frame.size.width, scroll_frame.size.height)
        )
        scroll_view.setDocumentView_(self.content_view)
        container.addSubview_(scroll_view)

        self.window.setContentView_(container)

        # Load entries into content view
        self.content_view.loadEntries_(entries)
        self._update_count()

        # Show window
        self.window.makeKeyAndOrderFront_(None)

    def searchChanged_(self, sender):
        """Handle search field changes."""
        query = sender.stringValue()
        self.content_view.filterWithQuery_(query)
        self._update_count()

    def _update_count(self):
        """Update the count label."""
        filtered = len(self.content_view.filtered_entries)
        total = len(self.content_view.all_entries)
        if filtered == total:
            self.count_label.setStringValue_(f"{total} transcriptions")
        else:
            self.count_label.setStringValue_(f"{filtered} of {total} transcriptions")


def show_history():
    """Show the native history viewer."""
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

    viewer = HistoryViewerApp.alloc().init()
    viewer.createWindow()

    app.activateIgnoringOtherApps_(True)
    app.run()


if __name__ == "__main__":
    show_history()
