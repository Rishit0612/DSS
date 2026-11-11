# DuoScreen — Windows Server

Stream a Windows display to an iPad, turning it into a second monitor.

## Prerequisites

- **Python 3.10+**
- **Windows 10/11** (uses DirectX screen capture via dxcam)
- **iTunes or Apple Devices app** installed (for USB connectivity)

## Quick Start

```bash
# 1. Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
python -m duoscreen.main
```

## Command-Line Options

| Flag          | Description                        | Default     |
|---------------|------------------------------------|-------------|
| `--monitor N` | Monitor index to capture (0-based) | 0           |
| `--fps N`     | Target frames per second           | 30          |
| `--quality N` | JPEG quality (1-100)               | 70          |
| `--port N`    | TCP listen port                    | 59000       |
| `--config P`  | Path to `config.json`              | config.json |

## Configuration File

Create `config.json` in the working directory to persist settings:

```json
{
  "capture_monitor": 0,
  "width": 1024,
  "height": 768,
  "fps": 30,
  "jpeg_quality": 70,
  "server_port": 59000,
  "host": "127.0.0.1"
}
```

Command-line flags override values from the config file.

## Connecting Your iPad

### USB (recommended — lowest latency)

1. Connect iPad to PC with a USB cable.
2. Trust the computer on the iPad when prompted.
3. The server will automatically create a USB tunnel via `pymobiledevice3`.
4. Open the DuoScreen iPad app — it connects to `localhost:59000`.

If automatic tunnelling fails, use **iproxy** manually:

```bash
iproxy 59000 59000
```

### Wi-Fi

1. Ensure both the PC and iPad are on the same network.
2. Start the server with `--host 0.0.0.0` so it listens on all interfaces:
   ```bash
   python -m duoscreen.main --host 0.0.0.0
   ```
3. In the iPad app enter the PC's local IP address and port 59000.

## Wire Protocol

The server and iPad app communicate over a simple binary protocol:

| Packet  | Layout |
|---------|--------|
| **Video** | `DUOS` (4 B) · type `0x01` (1 B) · payload_size LE uint32 (4 B) · timestamp_ms LE uint64 (8 B) · JPEG payload |
| **Input** | `DUOS` (4 B) · type `0x02` (1 B) · x float32 (4 B) · y float32 (4 B) · action uint8 (1 B) — 14 B total |
| **Config** | `DUOS` (4 B) · type `0x03` (1 B) · width LE uint16 (2 B) · height LE uint16 (2 B) · fps uint8 (1 B) — 10 B total |

All multi-byte integers are **little-endian**.

## Architecture

```
┌──────────────┐    TCP/USB     ┌──────────────┐
│ Windows PC   │ ──────────────→│   iPad App   │
│              │                │              │
│ ScreenCapture│  Video pkts →  │ Decode MJPEG │
│ FrameEncoder │                │ Display      │
│ DuoScreenSrv │  ← Input pkts │ Touch events │
│ InputInjector│                │              │
└──────────────┘                └──────────────┘
```

## Troubleshooting

- **"No iOS device found"** — Install iTunes / Apple Devices, reconnect, and trust.
- **High latency** — Lower `--quality` or `--fps`.
- **dxcam error** — The server falls back to `mss` automatically; performance may be lower.
- **Firewall** — Allow Python through Windows Firewall on port 59000 for Wi-Fi mode.

## License

MIT
