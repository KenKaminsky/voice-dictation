"""History viewer - exports to HTML and opens in browser."""

import subprocess
import tempfile
from pathlib import Path
from storage import get_history


def export_history_html() -> Path:
    """Export history to a nicely formatted HTML file."""
    history = get_history()
    entries = history.get_all()

    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Transcription History</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro', sans-serif;
            background: #1e1e1e;
            color: #fff;
            margin: 0;
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
        }
        h1 {
            margin: 0 0 20px 0;
            font-size: 24px;
            font-weight: 500;
        }
        .search {
            width: 100%;
            padding: 12px 16px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            background: #2d2d2d;
            color: #fff;
            margin-bottom: 20px;
        }
        .search:focus {
            outline: 2px solid #0a84ff;
        }
        .count {
            color: #888;
            margin-bottom: 15px;
            font-size: 14px;
        }
        .entry {
            background: #2d2d2d;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }
        .entry:nth-child(odd) {
            background: #363636;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .meta {
            color: #888;
            font-size: 13px;
        }
        .copy-btn {
            background: #0a84ff;
            color: #fff;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
        }
        .copy-btn:hover {
            background: #0077ed;
        }
        .copy-btn:active {
            background: #006adc;
        }
        .text {
            font-size: 15px;
            line-height: 1.5;
            white-space: pre-wrap;
        }
        .no-results {
            text-align: center;
            color: #888;
            padding: 40px;
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <h1>📝 Transcription History</h1>
    <input type="text" class="search" id="search" placeholder="Search transcriptions..." oninput="filterEntries()">
    <div class="count" id="count"></div>
    <div id="entries">
"""

    if not entries:
        html += '<div class="no-results">No transcriptions yet.</div>'
    else:
        for entry in entries:
            timestamp = entry.timestamp[:19].replace("T", " ")
            duration = f"{entry.duration_seconds:.1f}s"
            # Escape for HTML
            text_html = entry.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Escape for JavaScript string (backticks)
            text_js = entry.text.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
            text_search = entry.text.lower().replace("\\", "\\\\").replace('"', '\\"')

            html += f"""
        <div class="entry" data-text="{text_search}">
            <div class="header">
                <span class="meta">{timestamp} • {duration}</span>
                <button class="copy-btn" onclick="copyText(this, `{text_js}`)">📋 Copy</button>
            </div>
            <div class="text">{text_html}</div>
        </div>
"""

    html += """
    </div>
    <script>
        function copyText(btn, text) {
            navigator.clipboard.writeText(text).then(() => {
                const orig = btn.textContent;
                btn.textContent = '✓ Copied!';
                setTimeout(() => btn.textContent = orig, 1500);
            });
        }

        function filterEntries() {
            const query = document.getElementById('search').value.toLowerCase();
            const entries = document.querySelectorAll('.entry');
            let visible = 0;

            entries.forEach(entry => {
                const text = entry.getAttribute('data-text') || '';
                if (text.includes(query)) {
                    entry.classList.remove('hidden');
                    visible++;
                } else {
                    entry.classList.add('hidden');
                }
            });

            document.getElementById('count').textContent =
                `${visible} of ${entries.length} transcriptions`;
        }

        // Initial count
        filterEntries();
    </script>
</body>
</html>
"""

    # Write to temp file
    temp_dir = Path(tempfile.gettempdir())
    html_path = temp_dir / "voice_dictation_history.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return html_path


def show_history():
    """Export history to HTML and open in browser."""
    html_path = export_history_html()
    subprocess.run(["open", str(html_path)])


if __name__ == "__main__":
    show_history()
