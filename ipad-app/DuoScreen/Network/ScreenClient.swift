import Foundation
import Network
import UIKit

// MARK: - Connection State

enum ConnectionState: String {
    case disconnected = "Disconnected"
    case connecting   = "Connecting"
    case connected    = "Connected"
    case streaming    = "Streaming"
}

// MARK: - Screen Client

/// TCP client that connects to the DuoScreen Windows server, receives JPEG
/// video frames, and sends touch input events back.
class ScreenClient: ObservableObject {

    // MARK: Published properties

    @Published var connectionState: ConnectionState = .disconnected
    @Published var currentFrame: UIImage?
    @Published var fps: Double = 0.0
    @Published var latency: Double = 0.0

    // MARK: Private

    private var connection: NWConnection?
    private let queue = DispatchQueue(label: "com.duoscreen.network", qos: .userInteractive)
    private let decoder = FrameDecoder()

    /// Accumulation buffer for incoming TCP data
    private var buffer = Data()

    // FPS tracking
    private var frameCount: Int = 0
    private var fpsTimer: Timer?
    private var lastFPSUpdate = Date()

    // MARK: - Connect

    func connect(host: String, port: UInt16) {
        guard connectionState == .disconnected else { return }

        DispatchQueue.main.async {
            self.connectionState = .connecting
        }

        let nwHost = NWEndpoint.Host(host)
        let nwPort = NWEndpoint.Port(rawValue: port)!

        // TCP parameters with no TLS
        let params = NWParameters.tcp
        // Disable Nagle for lower latency
        if let ipOptions = params.defaultProtocolStack.internetProtocol as? NWProtocolIP.Options {
            // No special config needed at IP level for local connections
            _ = ipOptions
        }

        connection = NWConnection(host: nwHost, port: nwPort, using: params)

        connection?.stateUpdateHandler = { [weak self] state in
            guard let self = self else { return }
            switch state {
            case .ready:
                DispatchQueue.main.async {
                    self.connectionState = .connected
                }
                self.startFPSTimer()
                self.receiveLoop()

            case .failed(let error):
                print("[DuoScreen] Connection failed: \(error)")
                self.handleDisconnect()

            case .cancelled:
                self.handleDisconnect()

            case .waiting(let error):
                print("[DuoScreen] Connection waiting: \(error)")

            default:
                break
            }
        }

        connection?.start(queue: queue)
    }

    // MARK: - Disconnect

    func disconnect() {
        connection?.cancel()
        connection = nil
        handleDisconnect()
    }

    private func handleDisconnect() {
        DispatchQueue.main.async {
            self.connectionState = .disconnected
            self.currentFrame = nil
            self.fps = 0
            self.latency = 0
        }
        fpsTimer?.invalidate()
        fpsTimer = nil
        buffer = Data()
        frameCount = 0
    }

    // MARK: - Receive Loop

    /// Continuously reads data from the TCP connection, accumulates it in a
    /// buffer, and extracts complete video packets.
    private func receiveLoop() {
        guard let connection = connection else { return }

        connection.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, _, isComplete, error in
            guard let self = self else { return }

            if let error = error {
                print("[DuoScreen] Receive error: \(error)")
                self.handleDisconnect()
                return
            }

            if let data = data, !data.isEmpty {
                self.buffer.append(data)
                self.processBuffer()
            }

            if isComplete {
                self.handleDisconnect()
                return
            }

            // Continue receiving
            self.receiveLoop()
        }
    }

    /// Process the accumulation buffer, extracting complete packets.
    private func processBuffer() {
        while true {
            // Need at least the header (17 bytes) to know what we have
            guard buffer.count >= DuoScreenProtocol.VIDEO_HEADER_SIZE else { break }

            // Check for magic bytes at the start
            let magic = buffer[buffer.startIndex..<buffer.startIndex + 4]
            guard magic == DuoScreenProtocol.MAGIC else {
                // Lost sync — try to find the next magic sequence
                if let nextMagic = findMagic(in: buffer, from: 1) {
                    buffer = Data(buffer[nextMagic...])
                } else {
                    // No magic found, discard everything
                    buffer.removeAll()
                }
                continue
            }

            let packetType = buffer[buffer.startIndex + 4]

            switch packetType {
            case DuoScreenProtocol.PACKET_TYPE_VIDEO:
                // Parse video header
                guard let header = DuoScreenProtocol.VideoPacketHeader.parse(from: buffer) else {
                    // Corrupted header, skip past magic
                    buffer = Data(buffer[(buffer.startIndex + 4)...])
                    continue
                }

                let totalPacketSize = DuoScreenProtocol.VIDEO_HEADER_SIZE + Int(header.payloadSize)

                // Wait for complete packet
                guard buffer.count >= totalPacketSize else { return }

                // Extract JPEG payload
                let payloadStart = buffer.startIndex + DuoScreenProtocol.VIDEO_HEADER_SIZE
                let payloadEnd = payloadStart + Int(header.payloadSize)
                let jpegData = Data(buffer[payloadStart..<payloadEnd])

                // Remove processed bytes
                buffer = Data(buffer[payloadEnd...])

                // Decode and display
                if let frame = decoder.decode(jpegData: jpegData) {
                    // Calculate latency from packet timestamp
                    let nowMs = UInt64(Date().timeIntervalSince1970 * 1000)
                    let latencyMs = Double(nowMs - header.timestamp)

                    DispatchQueue.main.async {
                        self.currentFrame = frame
                        self.latency = latencyMs
                        if self.connectionState != .streaming {
                            self.connectionState = .streaming
                        }
                    }
                    frameCount += 1
                }

            case DuoScreenProtocol.PACKET_TYPE_CONFIG:
                guard buffer.count >= DuoScreenProtocol.CONFIG_PACKET_SIZE else { return }

                if let config = DuoScreenProtocol.parseConfigPacket(data: buffer) {
                    print("[DuoScreen] Config received: \(config.width)x\(config.height) @ \(config.fps) FPS")
                }

                // Consume the config packet
                buffer = Data(buffer[(buffer.startIndex + DuoScreenProtocol.CONFIG_PACKET_SIZE)...])

            default:
                // Unknown packet type — skip past magic to resync
                buffer = Data(buffer[(buffer.startIndex + 4)...])
            }
        }
    }

    /// Scan forward in the buffer to find the next occurrence of the MAGIC bytes.
    private func findMagic(in data: Data, from offset: Int) -> Data.Index? {
        let magicBytes: [UInt8] = [0x44, 0x55, 0x4F, 0x53]
        let start = data.startIndex + offset
        guard data.count - offset >= 4 else { return nil }

        for i in start...(data.endIndex - 4) {
            if data[i] == magicBytes[0] &&
               data[i+1] == magicBytes[1] &&
               data[i+2] == magicBytes[2] &&
               data[i+3] == magicBytes[3] {
                return i
            }
        }
        return nil
    }

    // MARK: - Send Touch

    /// Send a touch event to the Windows server.
    func sendTouchEvent(x: Float, y: Float, action: UInt8) {
        guard let connection = connection,
              connectionState == .streaming || connectionState == .connected else { return }

        let packet = DuoScreenProtocol.buildInputPacket(x: x, y: y, action: action)
        connection.send(content: packet, completion: .contentProcessed { error in
            if let error = error {
                print("[DuoScreen] Send touch error: \(error)")
            }
        })
    }

    // MARK: - FPS Tracking

    private func startFPSTimer() {
        lastFPSUpdate = Date()
        frameCount = 0

        DispatchQueue.main.async {
            self.fpsTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
                guard let self = self else { return }
                let now = Date()
                let elapsed = now.timeIntervalSince(self.lastFPSUpdate)
                if elapsed > 0 {
                    let currentFPS = Double(self.frameCount) / elapsed
                    self.fps = currentFPS
                }
                self.frameCount = 0
                self.lastFPSUpdate = now
            }
        }
    }
}
