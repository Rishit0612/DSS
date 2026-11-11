# 🖥️📱 DuoScreen

> **Turn your iPad into a wired secondary display for your Windows laptop.**

DuoScreen streams your Windows desktop to an iPad over USB, turning it into a true extended display you can drag windows to — like Apple's Sidecar, but for Windows.

## ✨ Features

- **Wired USB connection** — 1-5ms latency, no Wi-Fi needed
- **Extended display** — drag windows to your iPad like a real monitor
- **Touch input** — tap on iPad to click on Windows
- **Open source** — free forever

## 🚀 Quick Start

### Prerequisites
- **Windows laptop** with Python 3.10+
- **iPad** with iOS 16+
- **USB cable** (Lightning or USB-C)
- **iTunes** installed on Windows (provides USB tunneling)
- **Xcode** on a Mac (to build the iPad app)

### 1. Start the Windows Server

```bash
cd DuoScreen/windows-server
pip install -r requirements.txt
python -m duoscreen
```

### 2. Install iPad App

Open `DuoScreen/ipad-app/DuoScreen.xcodeproj` in Xcode, build to your iPad.

### 3. Connect

1. Plug iPad into your laptop via USB
2. The server auto-creates a USB tunnel
3. Tap **Connect** in the iPad app
4. Your screen streams to the iPad! 🎉

## 📁 Project Structure

```
DuoScreen/
├── windows-server/          # Python — screen capture + streaming
│   ├── duoscreen/
│   │   ├── main.py          # Entry point
│   │   ├── capture.py       # DXGI/dxcam screen capture
│   │   ├── encoder.py       # MJPEG encoding
│   │   ├── server.py        # Async TCP server
│   │   ├── protocol.py      # Wire protocol
│   │   ├── usb_tunnel.py    # USB tunnel via pymobiledevice3
│   │   └── input_injector.py# Touch → mouse injection
│   └── requirements.txt
│
├── ipad-app/                # Swift — display + touch input
│   ├── DuoScreen/
│   │   ├── App/             # SwiftUI app + main view
│   │   ├── Network/         # TCP client + protocol
│   │   ├── Rendering/       # Frame decoder + renderer
│   │   ├── Input/           # Touch event handler
│   │   └── Settings/        # Settings UI
│   └── DuoScreen.xcodeproj
│
└── README.md
```

## 🔧 Configuration

### CLI Options
```bash
python -m duoscreen --monitor 0 --fps 30 --quality 70 --port 59000
```

### Config File (`config.json`)
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

## 📋 Roadmap

- [x] **Phase 1**: Screen mirror over USB (MJPEG)
- [ ] **Phase 2**: Virtual display driver (true extended screen)
- [ ] **Phase 3**: Touch input + H.264 encoding
- [ ] **Phase 4**: System tray, auto-detect, Retina support

## 📄 License

MIT

