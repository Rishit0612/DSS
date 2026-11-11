import SwiftUI
import UIKit

// MARK: - Touch Action Constants

/// Touch action codes — must match the Windows server's input_injector mapping.
enum TouchAction: UInt8 {
    case began = 0   // touchesBegan → mouse_down
    case moved = 1   // touchesMoved → mouse_move
    case ended = 2   // touchesEnded → mouse_up
}

// MARK: - UIKit Touch Overlay View

/// A transparent UIView overlay that captures all touch events and normalizes
/// coordinates to 0.0–1.0 range relative to the view bounds.
class TouchOverlayView: UIView {

    /// Callback invoked on every touch event with normalized (x, y) and action.
    var onTouch: ((Float, Float, UInt8) -> Void)?

    override init(frame: CGRect) {
        super.init(frame: frame)
        isMultipleTouchEnabled = false
        backgroundColor = .clear
        isUserInteractionEnabled = true
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        isMultipleTouchEnabled = false
        backgroundColor = .clear
        isUserInteractionEnabled = true
    }

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = touches.first else { return }
        sendTouch(touch, action: .began)
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = touches.first else { return }
        sendTouch(touch, action: .moved)
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = touches.first else { return }
        sendTouch(touch, action: .ended)
    }

    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
        guard let touch = touches.first else { return }
        sendTouch(touch, action: .ended)
    }

    private func sendTouch(_ touch: UITouch, action: TouchAction) {
        let location = touch.location(in: self)
        let bounds = self.bounds
        guard bounds.width > 0, bounds.height > 0 else { return }

        // Normalize to 0.0–1.0
        let x = Float(max(0, min(1, location.x / bounds.width)))
        let y = Float(max(0, min(1, location.y / bounds.height)))

        onTouch?(x, y, action.rawValue)
    }
}

// MARK: - SwiftUI Wrapper

/// SwiftUI wrapper for TouchOverlayView. Place this as an overlay on the
/// screen renderer to capture touch input.
struct TouchOverlay: UIViewRepresentable {

    /// Called with (x, y, action) on every touch event.
    var onTouch: (Float, Float, UInt8) -> Void

    func makeUIView(context: Context) -> TouchOverlayView {
        let view = TouchOverlayView()
        view.onTouch = onTouch
        return view
    }

    func updateUIView(_ uiView: TouchOverlayView, context: Context) {
        uiView.onTouch = onTouch
    }
}
