import Foundation

/// DuoScreen wire protocol — all multi-byte integers are LITTLE-ENDIAN.
/// Must match the Windows server implementation exactly.
enum DuoScreenProtocol {

    // MARK: - Constants

    /// Magic bytes: ASCII "DUOS"
    static let MAGIC = Data([0x44, 0x55, 0x4F, 0x53])

    static let PACKET_TYPE_VIDEO:  UInt8 = 0x01
    static let PACKET_TYPE_INPUT:  UInt8 = 0x02
    static let PACKET_TYPE_CONFIG: UInt8 = 0x03

    /// Video packet header size: magic(4) + type(1) + payloadSize(4) + timestamp(8) = 17
    static let VIDEO_HEADER_SIZE = 17

    /// Input packet total size: magic(4) + type(1) + x(4) + y(4) + action(1) = 14
    static let INPUT_PACKET_SIZE = 14

    /// Config packet total size: magic(4) + type(1) + width(2) + height(2) + fps(1) = 10
    static let CONFIG_PACKET_SIZE = 10

    // MARK: - Video Packet Header

    struct VideoPacketHeader {
        let payloadSize: UInt32
        let timestamp: UInt64

        /// Parse a 17-byte video header from raw data.
        /// Returns nil if the data is too short, magic doesn't match, or type is wrong.
        static func parse(from data: Data) -> VideoPacketHeader? {
            guard data.count >= VIDEO_HEADER_SIZE else { return nil }

            // Validate magic
            let magic = data[data.startIndex..<data.startIndex + 4]
            guard magic == MAGIC else { return nil }

            // Validate packet type
            let packetType = data[data.startIndex + 4]
            guard packetType == PACKET_TYPE_VIDEO else { return nil }

            // Read payload size (UInt32, little-endian) at offset 5
            let payloadSize = data.withUnsafeBytes { buf -> UInt32 in
                let base = buf.baseAddress!.advanced(by: 5)
                return base.loadUnaligned(as: UInt32.self)
            }

            // Read timestamp (UInt64, little-endian) at offset 9
            let timestamp = data.withUnsafeBytes { buf -> UInt64 in
                let base = buf.baseAddress!.advanced(by: 9)
                return base.loadUnaligned(as: UInt64.self)
            }

            return VideoPacketHeader(
                payloadSize: UInt32(littleEndian: payloadSize),
                timestamp: UInt64(littleEndian: timestamp)
            )
        }
    }

    // MARK: - Input Packet

    /// Build a 14-byte input packet: magic(4) + type 0x02(1) + x(4) + y(4) + action(1)
    static func buildInputPacket(x: Float, y: Float, action: UInt8) -> Data {
        var data = Data(capacity: INPUT_PACKET_SIZE)

        // Magic
        data.append(MAGIC)

        // Type
        data.append(PACKET_TYPE_INPUT)

        // X as Float32 LE
        var xLE = x.bitPattern.littleEndian
        data.append(Data(bytes: &xLE, count: 4))

        // Y as Float32 LE
        var yLE = y.bitPattern.littleEndian
        data.append(Data(bytes: &yLE, count: 4))

        // Action
        data.append(action)

        return data
    }

    // MARK: - Config Packet

    /// Parse a 10-byte config packet: magic(4) + type(1) + width(2) + height(2) + fps(1)
    static func parseConfigPacket(data: Data) -> (width: UInt16, height: UInt16, fps: UInt8)? {
        guard data.count >= CONFIG_PACKET_SIZE else { return nil }

        // Validate magic
        let magic = data[data.startIndex..<data.startIndex + 4]
        guard magic == MAGIC else { return nil }

        // Validate type
        let packetType = data[data.startIndex + 4]
        guard packetType == PACKET_TYPE_CONFIG else { return nil }

        // Width (UInt16 LE) at offset 5
        let width = data.withUnsafeBytes { buf -> UInt16 in
            let base = buf.baseAddress!.advanced(by: 5)
            return base.loadUnaligned(as: UInt16.self)
        }

        // Height (UInt16 LE) at offset 7
        let height = data.withUnsafeBytes { buf -> UInt16 in
            let base = buf.baseAddress!.advanced(by: 7)
            return base.loadUnaligned(as: UInt16.self)
        }

        // FPS (UInt8) at offset 9
        let fps = data[data.startIndex + 9]

        return (width: UInt16(littleEndian: width), height: UInt16(littleEndian: height), fps: fps)
    }
}
