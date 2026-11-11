"""DSS Local Test Client (Desktop Preview & Input Test)

Run this on your laptop to verify that the DSS Windows server is
capturing and streaming your screen properly without needing an iPad.
"""

import socket
import struct
import time
import tkinter as tk
from io import BytesIO
from PIL import Image, ImageTk

MAGIC = b"DUOS"
PACKET_VIDEO = 0x01
PACKET_INPUT = 0x02
PACKET_CONFIG = 0x03

_VIDEO_HEADER_FMT = "<4sB I Q"
_VIDEO_HEADER_SIZE = struct.calcsize(_VIDEO_HEADER_FMT)

class DSSTestClient:
    def __init__(self, host="127.0.0.1", port=59000):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        
        # UI
        self.root = tk.Tk()
        self.root.title("DSS — Test Client Preview (iPad Simulator)")
        self.root.geometry("960x600")
        self.root.configure(bg="#1a1a1a")
        
        self.status_label = tk.Label(
            self.root, 
            text=f"Connecting to DSS Server at {host}:{port}...", 
            font=("Segoe UI", 12),
            fg="#00e5ff", 
            bg="#1a1a1a"
        )
        self.status_label.pack(side=tk.TOP, pady=6)
        
        self.canvas = tk.Label(self.root, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Touch / Mouse events
        self.canvas.bind("<Button-1>", lambda e: self.send_input(e, action=0))
        self.canvas.bind("<B1-Motion>", lambda e: self.send_input(e, action=1))
        self.canvas.bind("<ButtonRelease-1>", lambda e: self.send_input(e, action=2))
        
        self.img_tk = None
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.fps = 0.0

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(3.0)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(0.1)
            self.running = True
            self.status_label.config(text=f"Connected to DSS Server ({self.host}:{self.port}) | Receiving Stream", fg="#00e676")
            return True
        except Exception as e:
            self.status_label.config(text=f"Connection failed: {e}. Is DSS server running?", fg="#ff5252")
            return False

    def recv_exact(self, n):
        data = bytearray()
        while len(data) < n and self.running:
            try:
                chunk = self.sock.recv(n - len(data))
                if not chunk:
                    return None
                data.extend(chunk)
            except socket.timeout:
                self.root.update()
                continue
            except Exception:
                return None
        return bytes(data)

    def send_input(self, event, action):
        if not self.sock or not self.running:
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 0 or ch <= 0:
            return
        x_norm = max(0.0, min(1.0, float(event.x) / float(cw)))
        y_norm = max(0.0, min(1.0, float(event.y) / float(ch)))
        
        # Wire packet: Magic(4) + Type(1) + x(4 LE float) + y(4 LE float) + action(1 uint8)
        pkt = struct.pack("<4sB f f B", MAGIC, PACKET_INPUT, x_norm, y_norm, action)
        try:
            self.sock.sendall(pkt)
        except Exception:
            pass

    def loop(self):
        if not self.running:
            if not self.connect():
                self.root.after(2000, self.loop)
                return

        try:
            # Read 17-byte header
            header = self.recv_exact(_VIDEO_HEADER_SIZE)
            if not header:
                self.running = False
                self.status_label.config(text="Disconnected from server. Reconnecting...", fg="#ff9800")
                self.root.after(1000, self.loop)
                return

            magic, ptype, payload_size, timestamp_ms = struct.unpack(_VIDEO_HEADER_FMT, header)
            
            if magic == MAGIC and ptype == PACKET_VIDEO:
                jpeg_data = self.recv_exact(payload_size)
                if jpeg_data:
                    # Decode JPEG and display
                    img = Image.open(BytesIO(jpeg_data))
                    cw = max(100, self.canvas.winfo_width())
                    ch = max(100, self.canvas.winfo_height())
                    img.thumbnail((cw, ch), Image.Resampling.LANCZOS)
                    self.img_tk = ImageTk.PhotoImage(img)
                    self.canvas.config(image=self.img_tk)
                    
                    self.frame_count += 1
                    now = time.time()
                    if now - self.last_fps_time >= 1.0:
                        self.fps = self.frame_count / (now - self.last_fps_time)
                        self.frame_count = 0
                        self.last_fps_time = now
                        latency = int(time.time() * 1000) - timestamp_ms
                        self.status_label.config(
                            text=f"Streaming Active | {self.fps:.1f} FPS | Latency: ~{max(0, latency)}ms | Click & drag inside to test touch input",
                            fg="#00e676"
                        )
        except Exception as e:
            pass

        self.root.after(5, self.loop)

    def run(self):
        self.root.after(100, self.loop)
        self.root.mainloop()

if __name__ == "__main__":
    client = DSSTestClient()
    client.run()

