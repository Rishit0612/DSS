import UIKit

/// Decodes JPEG frame data into UIImage for display.
/// Phase 1: Uses UIImage(data:) for MJPEG decoding.
/// Phase 2: Could be extended with VideoToolbox for H.264 hardware decoding.
class FrameDecoder {

    /// Decode JPEG data into a UIImage.
    /// - Parameter jpegData: Raw JPEG bytes from the video packet payload.
    /// - Returns: A UIImage if decoding succeeds, nil otherwise.
    func decode(jpegData: Data) -> UIImage? {
        return UIImage(data: jpegData)
    }

    // MARK: - Phase 2 Placeholder

    // Future: H.264 / HEVC hardware-accelerated decoding via VideoToolbox
    //
    // func decodeH264(nalUnit: Data) -> CVPixelBuffer? {
    //     // Create VTDecompressionSession
    //     // Feed CMSampleBuffer with NAL units
    //     // Get CVPixelBuffer callback
    //     // Convert to UIImage or render via Metal
    //     return nil
    // }
}
