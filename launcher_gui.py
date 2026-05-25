"""
launcher_gui.py — macOS-friendly GUI launcher for the Pokemon Legacy Randomizer.

Shows a small "server running" status window (required so macOS considers the
.app properly open), runs the HTTP server in a background thread, and opens
the browser automatically.  Close the window to stop the server.
"""

import sys
import os
import socket
import threading
import subprocess
import time
import tkinter as tk
from tkinter import font as tkfont

# ── Make sure our bundled modules are importable ──────────────────────────────
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)


# ── Server bootstrap ──────────────────────────────────────────────────────────

def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _start_server(port: int, ready_event: threading.Event):
    """Run in a daemon thread — starts the HTTPServer from main.py."""
    import http.server
    import main as m   # import our server module

    server = http.server.HTTPServer(("127.0.0.1", port), m.Handler)
    ready_event.set()
    server.serve_forever()


# ── GUI ───────────────────────────────────────────────────────────────────────

class StatusWindow:
    BG        = "#0f0f1a"
    PANEL     = "#16213e"
    BORDER    = "#243561"
    ACCENT    = "#f5c518"
    TEXT      = "#dce3f0"
    MUTED     = "#7a8ba8"
    GREEN     = "#4caf7d"
    RED       = "#e94560"
    W, H      = 380, 220

    def __init__(self):
        self.port   = _find_free_port()
        self.url    = f"http://127.0.0.1:{self.port}"
        self._server_ok = False

        # ── Window ────────────────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title("Pokemon Legacy Randomizer")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)

        # Centre on screen
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - self.W) // 2
        y  = (sh - self.H) // 2
        self.root.geometry(f"{self.W}x{self.H}+{x}+{y}")

        self._build_ui()

        # ── Start server in background ────────────────────────────────────────
        ready = threading.Event()
        t = threading.Thread(target=self._run_server_thread,
                             args=(ready,), daemon=True)
        t.start()

        # Once server is ready, open browser
        threading.Thread(target=self._open_browser_when_ready,
                         args=(ready,), daemon=True).start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        r = self.root
        pad = 24

        # Title row
        top = tk.Frame(r, bg=self.PANEL, pady=16)
        top.pack(fill="x")
        tk.Label(top, text="⚡ Pokemon Legacy Randomizer",
                 bg=self.PANEL, fg=self.ACCENT,
                 font=("SF Pro Display", 14, "bold")).pack()
        tk.Label(top, text="Web UI running in your browser",
                 bg=self.PANEL, fg=self.MUTED,
                 font=("SF Pro Text", 11)).pack(pady=(2, 0))

        # Divider
        tk.Frame(r, bg=self.BORDER, height=1).pack(fill="x")

        # Status row
        status_frame = tk.Frame(r, bg=self.BG, pady=14)
        status_frame.pack(fill="x", padx=pad)

        tk.Label(status_frame, text="Status",
                 bg=self.BG, fg=self.MUTED,
                 font=("SF Pro Text", 10, "bold")).grid(row=0, column=0, sticky="w")

        self.status_dot   = tk.Label(status_frame, text="●",
                                     bg=self.BG, fg=self.ACCENT,
                                     font=("SF Pro Text", 13))
        self.status_dot.grid(row=1, column=0, sticky="w")

        self.status_label = tk.Label(status_frame, text="Starting…",
                                     bg=self.BG, fg=self.TEXT,
                                     font=("SF Pro Text", 12))
        self.status_label.grid(row=1, column=1, sticky="w", padx=(6, 0))

        # URL row
        tk.Label(status_frame, text="Address",
                 bg=self.BG, fg=self.MUTED,
                 font=("SF Pro Text", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(10, 0))

        self.url_label = tk.Label(status_frame, text=self.url,
                                  bg=self.BG, fg=self.MUTED,
                                  font=("SF Mono", 11),
                                  cursor="hand2")
        self.url_label.grid(row=3, column=0, columnspan=2, sticky="w")
        self.url_label.bind("<Button-1>", lambda e: self._open_url())

        # Button row
        btn_frame = tk.Frame(r, bg=self.BG)
        btn_frame.pack(fill="x", padx=pad, pady=(4, 16))

        self.open_btn = tk.Button(
            btn_frame, text="Open in Browser",
            bg=self.ACCENT, fg="#1a1200",
            font=("SF Pro Text", 12, "bold"),
            relief="flat", padx=16, pady=6,
            cursor="hand2",
            command=self._open_url,
        )
        self.open_btn.pack(side="left")

        self.quit_btn = tk.Button(
            btn_frame, text="Stop Server",
            bg=self.PANEL, fg=self.MUTED,
            font=("SF Pro Text", 11),
            relief="flat", padx=14, pady=6,
            cursor="hand2",
            command=self._on_close,
        )
        self.quit_btn.pack(side="right")

    # ── Server thread ─────────────────────────────────────────────────────────

    def _run_server_thread(self, ready_event: threading.Event):
        try:
            import http.server
            import main as m
            server = http.server.HTTPServer(("127.0.0.1", self.port), m.Handler)
            self._server_ok = True
            ready_event.set()
            self.root.after(0, self._set_running)
            server.serve_forever()
        except Exception as exc:
            ready_event.set()
            self.root.after(0, lambda: self._set_error(str(exc)))

    def _set_running(self):
        self.status_dot.config(fg=self.GREEN)
        self.status_label.config(text="Server running", fg=self.GREEN)
        self.url_label.config(fg=self.ACCENT)

    def _set_error(self, msg: str):
        self.status_dot.config(fg=self.RED)
        self.status_label.config(text=f"Error: {msg}", fg=self.RED)

    # ── Browser ───────────────────────────────────────────────────────────────

    def _open_browser_when_ready(self, ready_event: threading.Event):
        ready_event.wait(timeout=10)
        if self._server_ok:
            time.sleep(0.4)
            self._open_url()

    def _open_url(self):
        try:
            subprocess.Popen(["/usr/bin/open", self.url])
        except Exception:
            import webbrowser
            webbrowser.open(self.url)

    # ── Close ─────────────────────────────────────────────────────────────────

    def _on_close(self):
        self.root.destroy()
        # Force-exit so the whole process ends cleanly
        os._exit(0)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    StatusWindow()
