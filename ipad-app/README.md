# DuoScreen — iPad App

Use your iPad as a second display for your Windows PC, connected over USB or Wi-Fi.

## Requirements

- macOS with Xcode 15+ installed
- iPad running iOS 16.0 or later
- Apple Developer account (free or paid) for deploying to a physical device
- The DuoScreen Windows server running on your PC

## Project Setup

### Option A: Open the Xcode Project

1. Copy the `ipad-app/` folder to a Mac.
2. Open `DuoScreen.xcodeproj` in Xcode.
3. Select your development team under **Signing & Capabilities**.
4. Choose your connected iPad as the run destination.
5. Click **Run** (⌘R).

### Option B: Create a New Xcode Project (if pbxproj doesn't load)

1. In Xcode, choose **File → New → Project → App** (iOS).
2. Set:
   - **Product Name**: `DuoScreen`
   - **Bundle Identifier**: `com.duoscreen.app`
   - **Interface**: SwiftUI
   - **Language**: Swift
   - **Minimum Deployment**: iOS 16.0
3. Delete the auto-generated `ContentView.swift`.
4. Drag all `.swift` files from the `DuoScreen/` folder (App, Network, Rendering, Input, Settings) into the Xcode project navigator.
5. Copy `Info.plist` into the project and set it as the project's Info.plist in **Build Settings → Packaging → Info.plist File**.
6. Build and run on your iPad.

## Connecting to the Windows Server

### USB Connection (Recommended — lowest latency)

1. Install [libimobiledevice](https://libimobiledevice.org/) or [iTunes](https://www.apple.com/itunes/) on your Windows PC.
2. Connect your iPad to the PC via USB cable.
3. On your Mac (or Windows with iproxy), run:
   ```bash
   iproxy 59000 59000
   ```
   This tunnels `localhost:59000` on the iPad to `localhost:59000` on the PC.
4. In the DuoScreen iPad app, use the default settings:
   - **Host**: `127.0.0.1`
   - **Port**: `59000`
5. Start the Windows server, then tap **Connect** in the iPad app.

### Wi-Fi Connection

1. Make sure both the PC and iPad are on the same network.
2. Find your PC's local IP address (e.g., `192.168.1.100`).
3. In the DuoScreen iPad app settings, set:
   - **Host**: `192.168.1.100` (your PC's IP)
   - **Port**: `59000`
4. Start the Windows server with `--host 0.0.0.0` to listen on all interfaces.
5. Tap **Connect** in the iPad app.

## Settings

Access settings via the gear icon (⚙️) on the connection screen:

| Setting      | Default       | Description                          |
|-------------|---------------|--------------------------------------|
| Host        | `127.0.0.1`   | Server IP address                    |
| Port        | `59000`       | Server TCP port                      |
| Show FPS    | On            | Display FPS counter during streaming |
| Show Latency| Off           | Display latency overlay              |

## Architecture

```
DuoScreen/
├── App/
│   ├── DuoScreenApp.swift      # @main entry point
│   └── ContentView.swift       # Main UI (connect screen + streaming view)
├── Network/
│   ├── Protocol.swift          # Wire protocol (DUOS magic, packet formats)
│   └── ScreenClient.swift      # TCP client using Network.framework
├── Rendering/
│   ├── ScreenRenderer.swift    # UIImageView-based frame display
│   └── FrameDecoder.swift      # JPEG → UIImage decoder
├── Input/
│   └── TouchHandler.swift      # Touch capture + normalization
├── Settings/
│   └── SettingsView.swift      # SwiftUI settings form
└── Info.plist                  # App configuration
```

## Wire Protocol

All multi-byte integers are **little-endian**.

| Packet Type | Structure |
|------------|-----------|
| Video (0x01) | `DUOS`(4) + type(1) + payload_size(uint32, 4) + timestamp_ms(uint64, 8) + JPEG(payload_size) |
| Input (0x02) | `DUOS`(4) + type(1) + x(float32, 4) + y(float32, 4) + action(uint8, 1) = 14 bytes |
| Config (0x03) | `DUOS`(4) + type(1) + width(uint16, 2) + height(uint16, 2) + fps(uint8, 1) = 10 bytes |

## Troubleshooting

- **Can't connect**: Verify the server is running and the port/host are correct. For USB, ensure `iproxy` is running.
- **Lag / low FPS**: Lower the quality/resolution in the Windows server settings. USB connection is faster than Wi-Fi.
- **Black screen after connect**: The status should show "Streaming". If stuck on "Connected", the server may not be sending frames yet.
