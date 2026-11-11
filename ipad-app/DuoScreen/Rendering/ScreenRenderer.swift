import SwiftUI
import UIKit

/// A UIViewRepresentable that efficiently displays video frames using UIImageView.
/// Uses CALayer for minimal overhead when updating frames at high frequency.
struct ScreenRendererView: UIViewRepresentable {
    @Binding var image: UIImage?

    func makeUIView(context: Context) -> UIImageView {
        let imageView = UIImageView()
        imageView.contentMode = .scaleAspectFit
        imageView.backgroundColor = .black
        imageView.clipsToBounds = true

        // Optimize for frequent updates
        imageView.layer.drawsAsynchronously = true

        return imageView
    }

    func updateUIView(_ imageView: UIImageView, context: Context) {
        imageView.image = image
    }
}
