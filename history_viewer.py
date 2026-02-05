"""History viewer with search and copy functionality."""

import tkinter as tk
from tkinter import ttk
import pyperclip
from storage import get_history


class HistoryViewer:
    """A window to view and search transcription history."""

    def __init__(self):
        self.history = get_history()
        self.filtered_entries = []

        # Create main window
        self.root = tk.Tk()
        self.root.title("Transcription History")
        self.root.geometry("700x500")
        self.root.configure(bg="#1e1e1e")

        # Style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabel", background="#1e1e1e", foreground="#ffffff")
        style.configure("TEntry", fieldbackground="#2d2d2d", foreground="#ffffff")
        style.configure("TButton", background="#3d3d3d", foreground="#ffffff")

        self._create_widgets()
        self._load_entries()

    def _create_widgets(self):
        """Create the UI widgets."""
        # Search frame
        search_frame = ttk.Frame(self.root, padding=10)
        search_frame.pack(fill=tk.X)

        ttk.Label(search_frame, text="Search:", font=("SF Pro", 12)).pack(side=tk.LEFT, padx=(0, 10))

        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self._filter_entries())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50, font=("SF Pro", 12))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Count label
        self.count_label = ttk.Label(search_frame, text="", font=("SF Pro", 10))
        self.count_label.pack(side=tk.RIGHT, padx=(10, 0))

        # Main content with scrollbar
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Canvas for scrolling
        self.canvas = tk.Canvas(container, bg="#2d2d2d", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.canvas.yview)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Bind canvas resize to update frame width
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _on_canvas_configure(self, event):
        """Update frame width when canvas is resized."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _load_entries(self):
        """Load all entries from history."""
        self.all_entries = self.history.get_all()
        self._filter_entries()

    def _filter_entries(self):
        """Filter entries based on search query."""
        query = self.search_var.get().lower().strip()

        if query:
            self.filtered_entries = [
                e for e in self.all_entries
                if query in e.text.lower()
            ]
        else:
            self.filtered_entries = self.all_entries

        self._render_entries()
        self.count_label.configure(text=f"{len(self.filtered_entries)} of {len(self.all_entries)} entries")

    def _render_entries(self):
        """Render the filtered entries."""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.filtered_entries:
            label = tk.Label(
                self.scrollable_frame,
                text="No transcriptions found.",
                font=("SF Pro", 12),
                fg="#888888",
                bg="#2d2d2d",
                pady=20,
            )
            label.pack(fill=tk.X)
            return

        # Render each entry
        for i, entry in enumerate(self.filtered_entries):
            self._create_entry_widget(i, entry)

    def _create_entry_widget(self, index: int, entry):
        """Create a widget for a single entry."""
        # Entry frame
        frame = tk.Frame(
            self.scrollable_frame,
            bg="#3d3d3d" if index % 2 == 0 else "#2d2d2d",
            padx=10,
            pady=8,
        )
        frame.pack(fill=tk.X, pady=1)

        # Header row (timestamp, duration, copy button)
        header_frame = tk.Frame(frame, bg=frame["bg"])
        header_frame.pack(fill=tk.X)

        timestamp = entry.timestamp[:19].replace("T", " ")
        duration = f"{entry.duration_seconds:.1f}s"

        header_label = tk.Label(
            header_frame,
            text=f"{timestamp}  •  {duration}",
            font=("SF Pro", 10),
            fg="#888888",
            bg=frame["bg"],
            anchor="w",
        )
        header_label.pack(side=tk.LEFT)

        # Copy button
        copy_btn = tk.Button(
            header_frame,
            text="📋 Copy",
            font=("SF Pro", 10),
            fg="#ffffff",
            bg="#4a4a4a",
            activebackground="#5a5a5a",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=lambda t=entry.text: self._copy_text(t),
        )
        copy_btn.pack(side=tk.RIGHT)

        # Text content
        text_label = tk.Label(
            frame,
            text=entry.text,
            font=("SF Pro", 12),
            fg="#ffffff",
            bg=frame["bg"],
            anchor="w",
            justify=tk.LEFT,
            wraplength=600,
        )
        text_label.pack(fill=tk.X, pady=(5, 0))

    def _copy_text(self, text: str):
        """Copy text to clipboard."""
        pyperclip.copy(text)
        # Show brief feedback
        self.root.title("✓ Copied!")
        self.root.after(1000, lambda: self.root.title("Transcription History"))

    def run(self):
        """Run the viewer."""
        self.root.mainloop()


def show_history():
    """Show the history viewer window."""
    viewer = HistoryViewer()
    viewer.run()


if __name__ == "__main__":
    show_history()
