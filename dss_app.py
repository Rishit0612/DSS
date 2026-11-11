"""DSS Desktop Application (Windows GUI)

A modern, clean desktop GUI for Dual Screening Studio.
Just double click to open, click "SCREEN MODE: ON", and your iPad
instantly becomes a secondary screen.
"""

import asyncio
import os
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

# Ensure duoscreen package is importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(CURRENT_DIR, "windows-server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from duoscreen.capture import ScreenCapture
from duoscreen.config import DuoScreenConfig
from duoscreen.encoder import FrameEncoder
from duoscreen.input_injector import InputInjector
from duoscreen.server import DuoScreenServer
from duoscreen.usb_tunnel import USBTunnel
from duoscreen.web_server import WebStreamingServer

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

class DSSApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DSS — Dual Screening Studio")
        self.root.geometry("520x620")
        self.root.resizable(False, False)
        self.root.configure(bg="#0f172a")

        self.is_running = False
        self.server_thread = None
        self.loop = None
        self.local_ip = get_local_ip()

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#0f172a")
        header.pack(fill=tk.X, padx=24, pady=(24, 16))

        title = tk.Label(
            header,
            text="🖥️ Dual Screening Studio",
            font=("Segoe UI", 18, "bold"),
            fg="#f8fafc",
            bg="#0f172a"
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            header,
            text="Turn your iPad into a secondary display with 1-click",
            font=("Segoe UI", 10),
            fg="#94a3b8",
            bg="#0f172a"
        )
        subtitle.pack(anchor="w", pady=(2, 0))

        # Main Toggle Card
        card = tk.Frame(self.root, bg="#1e293b", highlightbackground="#334155", highlightthickness=1)
        card.pack(fill=tk.X, padx=24, pady=8)

        self.status_icon = tk.Label(
            card,
            text="⚪",
            font=("Segoe UI", 28),
            fg="#64748b",
            bg="#1e293b"
        )
        self.status_icon.pack(pady=(20, 4))

        self.status_text = tk.Label(
            card,
            text="SCREEN MODE IS OFF",
            font=("Segoe UI", 13, "bold"),
            fg="#94a3b8",
            bg="#1e293b"
        )
        self.status_text.pack(pady=(0, 16))

        # Big Action Button
        self.toggle_btn = tk.Button(
            card,
            text="⚡ TURN SCREEN MODE ON",
            font=("Segoe UI", 12, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=20,
            pady=12,
            cursor="hand2",
            command=self.toggle_screen_mode
        )
        self.toggle_btn.pack(fill=tk.X, padx=32, pady=(0, 24))

        # Connection Info Card
        info_card = tk.Frame(self.root, bg="#1e293b", highlightbackground="#334155", highlightthickness=1)
        info_card.pack(fill=tk.X, padx=24, pady=12)

        info_title = tk.Label(
            info_card,
            text="📱 iPad Connection Details",
            font=("Segoe UI", 11, "bold"),
            fg="#f8fafc",
            bg="#1e293b"
        )
        info_title.pack(anchor="w", padx=16, pady=(12, 6))

        self.ip_label = tk.Label(
            info_card,
            text=f"iPad App / Browser URL: http://{self.local_ip}:5000",
            font=("Segoe UI", 10, "bold"),
            fg="#38bdf8",
            bg="#1e293b"
        )
        self.ip_label.pack(anchor="w", padx=16, pady=2)

        tip_label = tk.Label(
            info_card,
            text="• 1-Time Setup: iPad Safari me ye link kholkar 'Add to Home Screen' karein.\n• Uske baad bas iPad par DSS icon dabayein aur screen on ho jayegi!",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b",
            justify=tk.LEFT
        )
        tip_label.pack(anchor="w", padx=16, pady=(4, 14))

        # Settings Section
        settings_frame = tk.Frame(self.root, bg="#0f172a")
        settings_frame.pack(fill=tk.X, padx=24, pady=8)

        # FPS Selection
        fps_frame = tk.Frame(settings_frame, bg="#0f172a")
        fps_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        tk.Label(fps_frame, text="Target Framerate", font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a").pack(anchor="w")
        self.fps_var = tk.StringVar(value="30 FPS")
        fps_menu = ttk.Combobox(fps_frame, textvariable=self.fps_var, values=["24 FPS", "30 FPS", "60 FPS"], state="readonly")
        fps_menu.pack(fill=tk.X, pady=4)

        # Quality Selection
        qual_frame = tk.Frame(settings_frame, bg="#0f172a")
        qual_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(8, 0))

        tk.Label(qual_frame, text="Stream Quality", font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a").pack(anchor="w")
        self.quality_var = tk.StringVar(value="High (80%)")
        qual_menu = ttk.Combobox(qual_frame, textvariable=self.quality_var, values=["Balanced (70%)", "High (80%)", "Ultra (90%)"], state="readonly")
        qual_menu.pack(fill=tk.X, pady=4)

        # Footer
        footer = tk.Label(
            self.root,
            text="DSS v1.0 • Low-latency Screen Streaming & Touch Control",
            font=("Segoe UI", 8),
            fg="#475569",
            bg="#0f172a"
        )
        footer.pack(side=tk.BOTTOM, pady=12)

    def toggle_screen_mode(self):
        if not self.is_running:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        self.is_running = True
        self.status_icon.config(text="🟢", fg="#22c55e")
        self.status_text.config(text="SCREEN MODE IS ACTIVE", fg="#4ade80")
        self.toggle_btn.config(
            text="⏹ STOP SCREEN MODE",
            bg="#ef4444",
            activebackground="#dc2626"
        )

        fps_val = int(self.fps_var.get().split()[0])
        quality_map = {"Balanced (70%)": 70, "High (80%)": 80, "Ultra (90%)": 90}
        quality_val = quality_map.get(self.quality_var.get(), 75)

        self.cfg = DuoScreenConfig(
            fps=fps_val,
            jpeg_quality=quality_val,
            server_port=59000
        )

        self.server_thread = threading.Thread(target=self._run_server_thread, daemon=True)
        self.server_thread.start()

    def _run_server_thread(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        capture = ScreenCapture()
        encoder = FrameEncoder()
        injector = InputInjector()
        server = DuoScreenServer()
        tunnel = USBTunnel()
        web_server = WebStreamingServer(host="0.0.0.0", port=5000)

        # Best-effort USB tunnel
        device = tunnel.find_device()
        if device is not None:
            tunnel.create_tunnel(device, self.cfg.server_port, self.cfg.server_port)

        capture.start(self.cfg.capture_monitor)

        # Mouse injection setup
        import ctypes
        user32 = ctypes.windll.user32
        mon_w = user32.GetSystemMetrics(0)
        mon_h = user32.GetSystemMetrics(1)
        monitor_bounds = (0, 0, mon_w, mon_h)

        def on_input(event: dict):
            injector.inject_mouse_event(
                event["x"],
                event["y"],
                event["action"],
                monitor_bounds,
            )

        server.set_input_callback(on_input)
        web_server.set_input_callback(on_input)

        stream_task = self.loop.create_task(server.stream_loop(capture, encoder, self.cfg, web_server=web_server))
        server_task = self.loop.create_task(server.start(self.cfg.host, self.cfg.server_port, capture, encoder, self.cfg))
        web_task = self.loop.create_task(web_server.start())

        try:
            self.loop.run_until_complete(asyncio.gather(server_task, stream_task, web_task, return_exceptions=True))
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        except Exception as e:
            print(f"[!] Server thread notice: {e}")
        finally:
            try:
                self.loop.run_until_complete(server.stop())
                self.loop.run_until_complete(web_server.stop())
            except Exception:
                pass
            capture.stop()
            tunnel.stop()

    def stop_server(self):
        self.is_running = False
        self.status_icon.config(text="⚪", fg="#64748b")
        self.status_text.config(text="SCREEN MODE IS OFF", fg="#94a3b8")
        self.toggle_btn.config(
            text="⚡ TURN SCREEN MODE ON",
            bg="#0284c7",
            activebackground="#0369a1"
        )

        if self.loop and self.loop.is_running():
            for task in asyncio.all_tasks(self.loop):
                task.cancel()

    def on_close(self):
        if self.is_running:
            self.stop_server()
        self.root.destroy()
        sys.exit(0)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = DSSApp()
    app.run()

