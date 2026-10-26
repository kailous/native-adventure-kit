import AppKit

enum ConsoleTheme {
    static func color(_ hex: UInt32) -> NSColor { NSColor(srgbRed: CGFloat((hex >> 16) & 255)/255, green: CGFloat((hex >> 8) & 255)/255, blue: CGFloat(hex & 255)/255, alpha: 1) }
    static let background = color(0x06121e)
    static let surface = color(0x132333)
    static let raised = color(0x29445e)
    static let gold = color(0xb9a165)
    static let mint = color(0x4cfeaa)
    static let text = color(0xfff9eb)
    static let muted = color(0x91a4b4)
    static let border = color(0x283b4a)
}

final class ConsoleSurface: NSView {
    var texture = false
    init() { super.init(frame: .zero); wantsLayer = true }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)
        if texture, let image = NSImage(contentsOf: Bundle.main.resourceURL!.appendingPathComponent("webui/branding/guide-sidebar/background.png")) {
            image.draw(in: bounds, from: .zero, operation: .sourceOver, fraction: 0.65)
        }
    }
}

/// AppKit actions share the web product's palette; native keyboard focus and accessibility remain available.
class ConsoleButton: NSButton {
    var primary = false
    private var sizeConstraint: NSLayoutConstraint?
    var controlHeight: CGFloat = 40 { didSet { sizeConstraint?.constant = controlHeight; invalidateIntrinsicContentSize() } }
    var symbol = ""
    private var hovered = false
    override init(frame frameRect: NSRect) { super.init(frame: frameRect); configure() }
    required init?(coder: NSCoder) { super.init(coder: coder); configure() }
    private func configure() { isBordered = false; focusRingType = .exterior; font = .systemFont(ofSize: 12, weight: .medium); sizeConstraint = heightAnchor.constraint(equalToConstant: controlHeight); sizeConstraint?.isActive = true }
    override var intrinsicContentSize: NSSize { NSSize(width: max(92, (title as NSString).size(withAttributes: [.font: font!]).width + 44), height: controlHeight) }
    override func updateTrackingAreas() { super.updateTrackingAreas(); trackingAreas.forEach(removeTrackingArea); addTrackingArea(NSTrackingArea(rect: bounds, options: [.mouseEnteredAndExited, .activeInKeyWindow, .inVisibleRect], owner: self)) }
    override func mouseEntered(with event: NSEvent) { hovered = true; needsDisplay = true }
    override func mouseExited(with event: NSEvent) { hovered = false; needsDisplay = true }
    override func draw(_ dirtyRect: NSRect) {
        let active = (hovered || isHighlighted) && isEnabled
        let bg = primary ? (active ? ConsoleTheme.text : ConsoleTheme.gold) : (active ? ConsoleTheme.raised : ConsoleTheme.surface)
        let fg = isEnabled ? (primary ? ConsoleTheme.background : ConsoleTheme.text) : ConsoleTheme.muted.withAlphaComponent(0.5)
        let rect = bounds.insetBy(dx: 1, dy: 1); let path = NSBezierPath(roundedRect: rect, xRadius: 9, yRadius: 9)
        (isEnabled ? bg : ConsoleTheme.surface).setFill(); path.fill()
        if !primary { (active ? ConsoleTheme.gold : ConsoleTheme.border).setStroke(); path.lineWidth = 1; path.stroke() }
        if window?.firstResponder === self { ConsoleTheme.mint.setStroke(); let focus = NSBezierPath(roundedRect: bounds.insetBy(dx: 2,dy: 2), xRadius: 8,yRadius: 8); focus.lineWidth = 2; focus.stroke() }
        let names = ["arrow.up.right":"export", "arrow.clockwise":"refresh", "slider.horizontal.3":"settings", "doc.text":"document", "folder":"folder", "doc.on.doc":"copy", "stop":"stop", "start":"chevron-right"]
        let icon = names[symbol].flatMap { NSImage(contentsOf: Bundle.main.resourceURL!.appendingPathComponent("webui/icons/reicon/\($0).svg")) }
        let textSize = (title as NSString).size(withAttributes: [.font: font!]); let total = textSize.width + (icon == nil ? 0 : 24)
        var x = (bounds.width-total)/2
        if let icon = icon {
            let tinted = NSImage(size: NSSize(width: 16, height: 16)); tinted.lockFocus(); icon.draw(in: NSRect(x: 0,y: 0,width: 16,height: 16)); fg.setFill(); NSRect(x: 0,y: 0,width: 16,height: 16).fill(using: .sourceAtop); tinted.unlockFocus()
            tinted.draw(in: NSRect(x: x,y: (bounds.height-16)/2,width: 16,height: 16)); x += 24
        }
        (title as NSString).draw(at: NSPoint(x: x,y: (bounds.height-textSize.height)/2), withAttributes: [.font: font!, .foregroundColor: fg])
    }
}

/// Single-address field retains the same shell as the network picker, without a menu affordance.
final class ConsoleAddressFrame: NSView {
    override func draw(_ dirtyRect: NSRect) {
        let path = NSBezierPath(roundedRect: bounds.insetBy(dx: 1, dy: 1), xRadius: 9, yRadius: 9)
        ConsoleTheme.surface.setFill(); path.fill()
        ConsoleTheme.border.setStroke(); path.lineWidth = 1; path.stroke()
    }
}

/// Keep the native popup menu and accessibility while matching the WebUI's 40-point control row.
final class ConsoleNetworkPicker: NSPopUpButton {
    private var hovered = false
    override init(frame buttonFrame: NSRect, pullsDown flag: Bool) { super.init(frame: buttonFrame, pullsDown: flag); heightAnchor.constraint(equalToConstant: 40).isActive = true }
    required init?(coder: NSCoder) { super.init(coder: coder) }
    override var intrinsicContentSize: NSSize { NSSize(width: 190, height: 40) }
    override func updateTrackingAreas() { super.updateTrackingAreas(); trackingAreas.forEach(removeTrackingArea); addTrackingArea(NSTrackingArea(rect: bounds, options: [.mouseEnteredAndExited, .activeInKeyWindow, .inVisibleRect], owner: self)) }
    override func mouseEntered(with event: NSEvent) { hovered = true; needsDisplay = true }
    override func mouseExited(with event: NSEvent) { hovered = false; needsDisplay = true }
    override func draw(_ dirtyRect: NSRect) {
        let path = NSBezierPath(roundedRect: bounds.insetBy(dx: 1, dy: 1), xRadius: 9, yRadius: 9)
        (hovered && isEnabled ? ConsoleTheme.raised : ConsoleTheme.surface).setFill(); path.fill()
        (hovered && isEnabled ? ConsoleTheme.gold : ConsoleTheme.border).setStroke(); path.lineWidth = 1; path.stroke()
        let fg = isEnabled ? ConsoleTheme.text : ConsoleTheme.muted.withAlphaComponent(0.5)
        let content = selectedItem?.title ?? "暂无局域网地址"
        let attrs: [NSAttributedString.Key: Any] = [.font: NSFont.monospacedSystemFont(ofSize: 12, weight: .regular), .foregroundColor: fg]
        let size = (content as NSString).size(withAttributes: attrs)
        (content as NSString).draw(at: NSPoint(x: 12, y: (bounds.height-size.height)/2), withAttributes: attrs)
        if let icon = NSImage(contentsOf: Bundle.main.resourceURL!.appendingPathComponent("webui/icons/reicon/chevron-down.svg")) {
            let tinted = NSImage(size: NSSize(width: 14, height: 14)); tinted.lockFocus(); icon.draw(in: NSRect(x: 0,y: 0,width: 14,height: 14)); fg.setFill(); NSRect(x: 0,y: 0,width: 14,height: 14).fill(using: .sourceAtop); tinted.unlockFocus()
            tinted.draw(in: NSRect(x: bounds.width-26, y: (bounds.height-14)/2, width: 14, height: 14))
        }
        if window?.firstResponder === self { ConsoleTheme.mint.setStroke(); path.lineWidth = 2; path.stroke() }
    }
}

/// Source artwork follows the Figma 55:1160 crop; content below it remains live native UI.
final class ConsoleHero: NSView {
    private let artwork = NSImage(contentsOf: Bundle.main.resourceURL!.appendingPathComponent("desktop-branding/hero.png"))
    override var isFlipped: Bool { true }
    override init(frame: NSRect) { super.init(frame: frame); wantsLayer = true }
    convenience init() { self.init(frame: .zero) }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func draw(_ dirtyRect: NSRect) {
        ConsoleTheme.background.setFill(); bounds.fill()
        let scale = bounds.width / 802
        artwork?.draw(in: NSRect(x: -413 * scale, y: -132 * scale, width: 1483 * scale, height: 834 * scale), from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
        if let context = NSGraphicsContext.current?.cgContext, let gradient = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: [ConsoleTheme.background.withAlphaComponent(0).cgColor, ConsoleTheme.background.cgColor] as CFArray, locations: [0, 1]) {
            context.drawLinearGradient(gradient, start: CGPoint(x: 0, y: 105 * scale), end: CGPoint(x: 0, y: 265 * scale), options: [.drawsAfterEndLocation])
        }
    }
}
final class ConsoleBrand: NSView {
    private let logo = NSImage(contentsOf: Bundle.main.resourceURL!.appendingPathComponent("webui/branding/map-ui/logo.svg"))
    private let badge = NSImage(contentsOf: Bundle.main.resourceURL!.appendingPathComponent("desktop-branding/badge.svg"))
    override var isFlipped: Bool { true }
    override func draw(_ dirtyRect: NSRect) {
        badge?.draw(in: NSRect(x: 16.23, y: 0, width: 146.045, height: 147), from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
        logo?.draw(in: NSRect(x: 0, y: 37.23, width: 178.5, height: 72.545), from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
    }
}
final class ConsoleIconButton: NSButton {
    private let source: NSImage?
    private var hovered = false
    init(icon: String, target: AnyObject?, action: Selector) {
        source = NSImage(contentsOf: Bundle.main.resourceURL!.appendingPathComponent("webui/icons/reicon/\(icon).svg"))
        super.init(frame: .zero); self.target = target; self.action = action; isBordered = false
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func updateTrackingAreas() { super.updateTrackingAreas(); trackingAreas.forEach(removeTrackingArea); addTrackingArea(NSTrackingArea(rect: bounds, options: [.mouseEnteredAndExited, .activeInKeyWindow, .inVisibleRect], owner: self)) }
    override func mouseEntered(with event: NSEvent) { hovered = true; needsDisplay = true }
    override func mouseExited(with event: NSEvent) { hovered = false; needsDisplay = true }
    override func draw(_ dirtyRect: NSRect) {
        let path = NSBezierPath(roundedRect: bounds.insetBy(dx: 1, dy: 1), xRadius: 20, yRadius: 20)
        (hovered || isHighlighted ? ConsoleTheme.raised : ConsoleTheme.surface).setFill(); path.fill()
        if hovered || window?.firstResponder === self { ConsoleTheme.gold.setStroke(); path.lineWidth = 1; path.stroke() }
        if let source = source {
            let tinted = NSImage(size: NSSize(width: 28, height: 28)); tinted.lockFocus(); source.draw(in: NSRect(x: 0, y: 0, width: 28, height: 28)); ConsoleTheme.gold.setFill(); NSRect(x: 0, y: 0, width: 28, height: 28).fill(using: .sourceAtop); tinted.unlockFocus()
            tinted.draw(in: NSRect(x: (bounds.width-28)/2, y: (bounds.height-28)/2, width: 28, height: 28))
        }
    }
}
