import SwiftUI

struct ContentView: View {
    @StateObject private var client = ScreenClient()
    @State private var showSettings = false

    @AppStorage("serverHost") private var serverHost = "127.0.0.1"
    @AppStorage("serverPort") private var serverPort = "59000"
    @AppStorage("showFPS") private var showFPS = true
    @AppStorage("showLatency") private var showLatency = false

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            if client.connectionState == .streaming, client.currentFrame != nil {
                // Full-screen streaming view with touch overlay
                ZStack {
                    ScreenRendererView(image: $client.currentFrame)
                        .ignoresSafeArea()

                    TouchOverlay { x, y, action in
                        client.sendTouchEvent(x: x, y: y, action: action)
                    }
                    .ignoresSafeArea()

                    // HUD overlay
                    VStack {
                        HStack {
                            Spacer()
                            if showFPS {
                                Text(String(format: "%.0f FPS", client.fps))
                                    .font(.caption)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(.black.opacity(0.6))
                                    .foregroundColor(.green)
                                    .cornerRadius(6)
                            }
                            if showLatency {
                                Text(String(format: "%.0f ms", client.latency))
                                    .font(.caption)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(.black.opacity(0.6))
                                    .foregroundColor(.yellow)
                                    .cornerRadius(6)
                            }
                        }
                        .padding(.top, 8)
                        .padding(.trailing, 16)
                        Spacer()
                    }
                }
                .statusBarHidden(true)
            } else {
                // Connection UI
                VStack(spacing: 24) {
                    Spacer()

                    Image(systemName: "display")
                        .font(.system(size: 72))
                        .foregroundColor(.blue)

                    Text("DuoScreen")
                        .font(.largeTitle.bold())
                        .foregroundColor(.white)

                    Text("Use your iPad as a wireless display")
                        .font(.subheadline)
                        .foregroundColor(.gray)

                    // Connection status
                    HStack(spacing: 8) {
                        Circle()
                            .fill(statusColor)
                            .frame(width: 10, height: 10)
                        Text(statusText)
                            .font(.callout)
                            .foregroundColor(.secondary)
                    }
                    .padding(.top, 8)

                    // Connect / Disconnect button
                    Button(action: {
                        if client.connectionState == .disconnected {
                            let port = UInt16(serverPort) ?? 59000
                            client.connect(host: serverHost, port: port)
                        } else {
                            client.disconnect()
                        }
                    }) {
                        Text(client.connectionState == .disconnected ? "Connect" : "Disconnect")
                            .font(.headline)
                            .frame(width: 200, height: 50)
                            .background(client.connectionState == .disconnected ? Color.blue : Color.red)
                            .foregroundColor(.white)
                            .cornerRadius(12)
                    }
                    .disabled(client.connectionState == .connecting)

                    if client.connectionState == .connecting {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    }

                    Spacer()
                }

                // Settings gear
                VStack {
                    HStack {
                        Spacer()
                        Button(action: { showSettings = true }) {
                            Image(systemName: "gear")
                                .font(.title2)
                                .foregroundColor(.white)
                                .padding()
                        }
                    }
                    Spacer()
                }
            }
        }
        .sheet(isPresented: $showSettings) {
            SettingsView()
        }
    }

    private var statusColor: Color {
        switch client.connectionState {
        case .disconnected: return .red
        case .connecting: return .yellow
        case .connected: return .orange
        case .streaming: return .green
        }
    }

    private var statusText: String {
        switch client.connectionState {
        case .disconnected: return "Disconnected"
        case .connecting: return "Connecting…"
        case .connected: return "Connected"
        case .streaming: return "Streaming"
        }
    }
}
