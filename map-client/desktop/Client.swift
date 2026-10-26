import AppKit
import CoreImage
import Darwin

final class Client: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var window: NSWindow!
    var bindingsWindow: KeyBindingsWindow?
    var backend: Process?
    var timer: Timer?
    var progressTimer: Timer?
    var tunnelInfo: [String: Any] = [:]
    var pendingTunnelRequest: [String: Any]?
    var tunnelRequestRunning = false
    var connection: [String: Any]?
    var startingAt = Date()
    let logView = NSTextView()
    let detailedLogs = NSButton(checkboxWithTitle: "详细日志", target: nil, action: nil)
    var consoleTimer: Timer?
    var events: [String] = []
    var eventValues: [String: String] = [:]
    var readingLogs = false
    var importingDataPacks = false
    var pendingDataPacks: [URL] = []
    let settings = UserDefaults.standard
    let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent(Client.nativeEdition ? "TOTK Native Map" : "TOTK Offline", isDirectory: true)
    var runtime: URL { support.appendingPathComponent("connection.json") }
    var logURL: URL { support.appendingPathComponent("service.log") }
    let status = NSTextField(labelWithString: "正在启动服务…")
    let telemetryStatus = NSTextField(labelWithString: "等待游戏启动 · 无需坐标校准")
    let progress = NSTextField(labelWithString: "等待存档同步")
    let localAddress = NSTextField(labelWithString: "")
    let phoneAddress = NSTextField(labelWithString: "")
    let qr = NSImageView()
    let qrPlaceholder = NSTextField(labelWithString: "等待服务启动")
    let networks = ConsoleNetworkPicker(frame: .zero, pullsDown: false)
    let networkAddress = NSTextField(labelWithString: "等待服务启动")
    let serviceButton = ConsoleButton(title: "停止服务", target: nil, action: nil)
    func button(_ title: String, _ action: Selector) -> NSButton { NSButton(title: title, target: self, action: action) }
    let serviceDot = NSTextField(labelWithString: "●")
    let saveDot = NSTextField(labelWithString: "●")
    let modDot = NSTextField(labelWithString: "●")
    let mcpState = NSTextField(labelWithString: "等待服务启动")
    let saveDate = NSTextField(labelWithString: "自动查找最新有效存档")
    let qrHint = NSTextField(wrappingLabelWithString: "服务启动后生成二维码")
    let feedback = NSTextField(labelWithString: "客户端保持运行，地图与同步服务即可持续使用。")
    var mapButton: ConsoleButton!
    var copyButton: ConsoleButton!
    var mcpButton: ConsoleButton!
    var mcpCopyButton: ConsoleButton!
    func label(_ text: String, _ size: CGFloat = 13, _ color: NSColor = ConsoleTheme.text, _ weight: NSFont.Weight = .regular) -> NSTextField {
        let v = NSTextField(wrappingLabelWithString: text); v.font = .systemFont(ofSize: size, weight: weight); v.textColor = color; return v
    }
    func column(_ views: [NSView], spacing: CGFloat = 12) -> NSStackView {
        let stack = NSStackView(views: views); stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = spacing; return stack
    }
    func row(_ views: [NSView], spacing: CGFloat = 12) -> NSStackView {
        let stack = NSStackView(views: views); stack.orientation = .horizontal; stack.alignment = .centerY; stack.distribution = .fill; stack.spacing = spacing; return stack
    }
    func action(_ text: String, _ icon: String, _ selector: Selector, primary: Bool = false) -> ConsoleButton {
        let b = ConsoleButton(title: text, target: self, action: selector); b.symbol = icon; b.primary = primary; if primary { b.font = .systemFont(ofSize: 14, weight: .semibold) }; b.setAccessibilityLabel(text); return b
    }
    func rule() -> NSView { let v = NSView(); v.wantsLayer = true; v.layer?.backgroundColor = ConsoleTheme.border.cgColor; v.heightAnchor.constraint(equalToConstant: 1).isActive = true; return v }
    func fill(_ child: NSView, in parent: NSView, inset: CGFloat = 24) {
        parent.addSubview(child); child.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([child.topAnchor.constraint(equalTo: parent.topAnchor, constant: inset), child.leadingAnchor.constraint(equalTo: parent.leadingAnchor, constant: inset), child.trailingAnchor.constraint(equalTo: parent.trailingAnchor, constant: -inset), child.bottomAnchor.constraint(equalTo: parent.bottomAnchor, constant: -inset)])
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        makeMenu()
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1151, height: 776), styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = Self.nativeEdition ? "王国之泪 · 原生游戏地图" : "王国之泪 · 交互地图"; window.delegate = self
        window.contentMinSize = NSSize(width: 1151, height: 776); window.contentMaxSize = window.contentMinSize
        window.appearance = NSAppearance(named: .darkAqua); window.backgroundColor = ConsoleTheme.surface
        window.titlebarAppearsTransparent = true; window.isMovableByWindowBackground = true
        let root = NSView(); window.contentView = root
        let sidebar = ConsoleSurface(); sidebar.texture = true; sidebar.layer?.backgroundColor = ConsoleTheme.background.cgColor; sidebar.layer?.cornerRadius = 20; sidebar.layer?.masksToBounds = true
        let hero = ConsoleHero(); hero.layer?.cornerRadius = 20; hero.layer?.masksToBounds = true
        let states = ConsoleSurface(); states.layer?.backgroundColor = ConsoleTheme.background.cgColor; states.layer?.cornerRadius = 20
        for v in [sidebar, hero, states] { root.addSubview(v); v.translatesAutoresizingMaskIntoConstraints = false }
        NSLayoutConstraint.activate([
            sidebar.topAnchor.constraint(equalTo: root.topAnchor, constant: 10), sidebar.bottomAnchor.constraint(equalTo: root.bottomAnchor, constant: -10), sidebar.leadingAnchor.constraint(equalTo: root.leadingAnchor, constant: 10), sidebar.widthAnchor.constraint(equalToConstant: 319),
            hero.leadingAnchor.constraint(equalTo: sidebar.trailingAnchor, constant: 10), hero.trailingAnchor.constraint(equalTo: root.trailingAnchor, constant: -10), hero.topAnchor.constraint(equalTo: sidebar.topAnchor), hero.bottomAnchor.constraint(equalTo: states.topAnchor, constant: -10),
            states.leadingAnchor.constraint(equalTo: hero.leadingAnchor), states.trailingAnchor.constraint(equalTo: hero.trailingAnchor), states.bottomAnchor.constraint(equalTo: sidebar.bottomAnchor), states.heightAnchor.constraint(equalToConstant: 150)])
        let brand = ConsoleBrand(); brand.setAccessibilityLabel("塞尔达传说 王国之泪")
        let title = label("王国之泪\n交互地图", 20, ConsoleTheme.text, .bold)
        let version = label("v " + (Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? ""), 12, ConsoleTheme.muted)
        for v in [brand, title, version] { sidebar.addSubview(v); v.translatesAutoresizingMaskIntoConstraints = false }
        NSLayoutConstraint.activate([brand.leadingAnchor.constraint(equalTo: sidebar.leadingAnchor, constant: 20), brand.topAnchor.constraint(equalTo: sidebar.topAnchor, constant: 60), brand.widthAnchor.constraint(equalToConstant: 178.5), brand.heightAnchor.constraint(equalToConstant: 147), title.trailingAnchor.constraint(equalTo: sidebar.trailingAnchor, constant: -20), title.topAnchor.constraint(equalTo: brand.topAnchor, constant: 18), version.trailingAnchor.constraint(equalTo: title.trailingAnchor), version.bottomAnchor.constraint(equalTo: brand.bottomAnchor, constant: -18)])
        let qrFrame = ConsoleSurface(); qrFrame.layer?.backgroundColor = NSColor.white.cgColor; qrFrame.layer?.cornerRadius = 10
        sidebar.addSubview(qrFrame); qrFrame.translatesAutoresizingMaskIntoConstraints = false
        qr.imageScaling = .scaleNone; qrFrame.addSubview(qr); qr.translatesAutoresizingMaskIntoConstraints = false
        qrPlaceholder.font = .systemFont(ofSize: 14); qrPlaceholder.textColor = ConsoleTheme.surface; qrFrame.addSubview(qrPlaceholder); qrPlaceholder.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([qrFrame.leadingAnchor.constraint(equalTo: sidebar.leadingAnchor, constant: 20), qrFrame.trailingAnchor.constraint(equalTo: sidebar.trailingAnchor, constant: -20), qrFrame.topAnchor.constraint(equalTo: sidebar.topAnchor, constant: 280), qrFrame.heightAnchor.constraint(equalTo: qrFrame.widthAnchor), qr.widthAnchor.constraint(equalToConstant: 248), qr.heightAnchor.constraint(equalToConstant: 248), qr.centerXAnchor.constraint(equalTo: qrFrame.centerXAnchor), qr.centerYAnchor.constraint(equalTo: qrFrame.centerYAnchor), qrPlaceholder.centerXAnchor.constraint(equalTo: qrFrame.centerXAnchor), qrPlaceholder.centerYAnchor.constraint(equalTo: qrFrame.centerYAnchor)])
        mapButton = action("启动服务", "start", #selector(launchOrOpen), primary: true); mapButton.keyEquivalent = "\r"; mapButton.controlHeight = 48; mapButton.font = .systemFont(ofSize: 20, weight: .bold)
        qrHint.font = .systemFont(ofSize: 12); qrHint.textColor = ConsoleTheme.muted
        let access = column([mapButton, qrHint], spacing: 10)
        sidebar.addSubview(access); access.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([access.leadingAnchor.constraint(equalTo: sidebar.leadingAnchor, constant: 20), access.trailingAnchor.constraint(equalTo: sidebar.trailingAnchor, constant: -20), access.bottomAnchor.constraint(equalTo: sidebar.bottomAnchor, constant: -30), mapButton.widthAnchor.constraint(equalTo: access.widthAnchor), qrHint.widthAnchor.constraint(equalTo: access.widthAnchor), qrHint.heightAnchor.constraint(equalToConstant: 32)])
        // The network selector and copy action complete the QR flow without competing with it.
        networks.target = self; networks.action = #selector(updateQR); networks.font = .monospacedSystemFont(ofSize: 12, weight: .regular); networks.setAccessibilityLabel("手机连接的局域网地址"); networks.widthAnchor.constraint(equalToConstant: 177).isActive = true
        copyButton = action("复制链接", "doc.on.doc", #selector(copyPhone)); copyButton.font = .systemFont(ofSize: 11)
        let networkSlot = ConsoleAddressFrame(); networkSlot.widthAnchor.constraint(equalToConstant: 177).isActive = true; networkSlot.heightAnchor.constraint(equalToConstant: 40).isActive = true
        networkSlot.addSubview(networks); networks.translatesAutoresizingMaskIntoConstraints = false
        networkAddress.font = .monospacedSystemFont(ofSize: 12, weight: .regular); networkAddress.textColor = ConsoleTheme.text; networkAddress.isSelectable = true
        networkSlot.addSubview(networkAddress); networkAddress.translatesAutoresizingMaskIntoConstraints = false; networks.isHidden = true
        NSLayoutConstraint.activate([networks.leadingAnchor.constraint(equalTo: networkSlot.leadingAnchor), networks.centerYAnchor.constraint(equalTo: networkSlot.centerYAnchor), networkAddress.leadingAnchor.constraint(equalTo: networkSlot.leadingAnchor, constant: 12), networkAddress.trailingAnchor.constraint(equalTo: networkSlot.trailingAnchor, constant: -12), networkAddress.centerYAnchor.constraint(equalTo: networkSlot.centerYAnchor)])
        let networkRow = row([networkSlot, copyButton], spacing: 8)
        sidebar.addSubview(networkRow); networkRow.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([networkRow.leadingAnchor.constraint(equalTo: qrFrame.leadingAnchor), networkRow.trailingAnchor.constraint(equalTo: qrFrame.trailingAnchor), networkRow.topAnchor.constraint(equalTo: qrFrame.bottomAnchor, constant: 12)])
        status.font = .systemFont(ofSize: 14, weight: .semibold); status.textColor = ConsoleTheme.text
        serviceDot.font = .systemFont(ofSize: 10); serviceDot.textColor = ConsoleTheme.gold
        detailedLogs.font = .systemFont(ofSize: 12); detailedLogs.contentTintColor = ConsoleTheme.muted; detailedLogs.target = self; detailedLogs.action = #selector(toggleLogDetail)
        let operations = NSPopUpButton(frame: .zero, pullsDown: true); operations.addItem(withTitle: "服务操作"); operations.bezelStyle = .rounded; operations.font = .systemFont(ofSize: 12)
        for (name, selector) in [("重新启动", #selector(restart)), ("停止服务", #selector(stopService)), ("导入数据包…", #selector(importDataPacks)), ("打开数据包目录", #selector(showDataPacks)), ("打开日志文件", #selector(showLog)), ("复制手机链接", #selector(copyPhone))] { let item = NSMenuItem(title: name, action: selector, keyEquivalent: ""); item.target = self; operations.menu?.addItem(item) }
        if Self.nativeEdition {
            let launch = action("启动游戏", "play.fill", #selector(launchNativeGame), primary: true)
            let keys = action("键位设置", "keyboard", #selector(editNativeKeys))
            let choose = action("选择游戏", "folder", #selector(chooseNativeGame))
            let gameActions = row([launch, keys, choose], spacing: 12)
            hero.addSubview(gameActions); gameActions.translatesAutoresizingMaskIntoConstraints = false
            NSLayoutConstraint.activate([gameActions.leadingAnchor.constraint(equalTo: hero.leadingAnchor, constant: 23), gameActions.topAnchor.constraint(equalTo: hero.topAnchor, constant: 190), launch.widthAnchor.constraint(equalToConstant: 130), keys.widthAnchor.constraint(equalToConstant: 120), choose.widthAnchor.constraint(equalToConstant: 120)])
        }
        let toolbar = row([row([status, serviceDot], spacing: 8), NSView(), detailedLogs, operations])
        hero.addSubview(toolbar); toolbar.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([toolbar.topAnchor.constraint(equalTo: hero.topAnchor, constant: 245), toolbar.leadingAnchor.constraint(equalTo: hero.leadingAnchor, constant: 23), toolbar.trailingAnchor.constraint(equalTo: hero.trailingAnchor, constant: -23)])
        let scroll = NSScrollView(); scroll.drawsBackground = false; scroll.hasVerticalScroller = true; scroll.autohidesScrollers = true; scroll.borderType = .noBorder
        logView.isEditable = false; logView.isSelectable = true; logView.drawsBackground = false; logView.font = .monospacedSystemFont(ofSize: 12, weight: .regular); logView.textColor = ConsoleTheme.muted; logView.textContainerInset = NSSize(width: 0, height: 8); logView.isVerticallyResizable = true; logView.isHorizontallyResizable = false; logView.autoresizingMask = [.width]; logView.textContainer?.widthTracksTextView = true
        scroll.documentView = logView
        hero.addSubview(scroll); scroll.translatesAutoresizingMaskIntoConstraints = false
        feedback.font = .systemFont(ofSize: 11); feedback.textColor = ConsoleTheme.muted
        hero.addSubview(feedback); feedback.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([scroll.topAnchor.constraint(equalTo: toolbar.bottomAnchor, constant: 8), scroll.leadingAnchor.constraint(equalTo: toolbar.leadingAnchor), scroll.trailingAnchor.constraint(equalTo: toolbar.trailingAnchor), scroll.bottomAnchor.constraint(equalTo: feedback.topAnchor, constant: -12), feedback.leadingAnchor.constraint(equalTo: toolbar.leadingAnchor), feedback.trailingAnchor.constraint(equalTo: toolbar.trailingAnchor), feedback.bottomAnchor.constraint(equalTo: hero.bottomAnchor, constant: -20)])
        logView.frame = NSRect(x: 0, y: 0, width: 730, height: 200)
        saveDate.font = .systemFont(ofSize: 12); saveDate.textColor = ConsoleTheme.muted; saveDate.maximumNumberOfLines = 2
        progress.font = .systemFont(ofSize: 11); progress.textColor = ConsoleTheme.muted; progress.maximumNumberOfLines = 2
        telemetryStatus.font = .systemFont(ofSize: 12); telemetryStatus.textColor = ConsoleTheme.muted; telemetryStatus.maximumNumberOfLines = 3
        mcpState.font = .systemFont(ofSize: 12); mcpState.textColor = ConsoleTheme.muted; mcpState.maximumNumberOfLines = 2
        mcpButton = action("连接配置", "slider.horizontal.3", #selector(showMCP)); mcpCopyButton = action("复制配置", "doc.on.doc", #selector(copyMCP))
        let saveTile = statusTile("存档同步", icon: "folder", dot: saveDot, lines: [saveDate, progress], selector: #selector(chooseSave))
        let modTile = statusTile("游戏", icon: "target", dot: modDot, lines: [telemetryStatus], selector: #selector(showModInfo))
        let copyConfig = NSButton(title: "复制配置", target: self, action: #selector(copyMCP)); copyConfig.isBordered = false; copyConfig.font = .systemFont(ofSize: 11); copyConfig.contentTintColor = ConsoleTheme.gold; copyConfig.alignment = .left
        let mcpTile = statusTile("MCP 连接", icon: "settings", dot: mcpDot, lines: [mcpState, copyConfig], selector: #selector(showMCP))
        let tiles = row([saveTile, modTile, mcpTile], spacing: 20); tiles.distribution = .fillEqually; tiles.alignment = .top
        states.addSubview(tiles); tiles.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([tiles.leadingAnchor.constraint(equalTo: states.leadingAnchor, constant: 27), tiles.trailingAnchor.constraint(equalTo: states.trailingAnchor, constant: -27), tiles.topAnchor.constraint(equalTo: states.topAnchor, constant: 42), tiles.bottomAnchor.constraint(lessThanOrEqualTo: states.bottomAnchor, constant: -18)])
        // Existing service controls remain available through the native menu.
        serviceButton.target = self; serviceButton.action = #selector(toggleService)
        consoleTimer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in self?.refreshConsole() }
        #if CLIENT_UI_PROBE
        renderNativePreview()
        NSApp.terminate(nil)
        #else
        window.center(); window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        if pendingDataPacks.isEmpty { startBackend() } else { let urls = pendingDataPacks; pendingDataPacks = []; installDataPacks(urls) }
        #endif
    }
    let mcpDot = NSTextField(labelWithString: "●")
    func statusTile(_ title: String, icon: String, dot: NSTextField, lines: [NSView], selector: Selector) -> NSView {
        let iconButton = ConsoleIconButton(icon: icon, target: self, action: selector); iconButton.setAccessibilityLabel(title + "设置"); iconButton.toolTip = title == "存档同步" ? "选择存档目录" : title == "MCP 连接" ? "查看连接配置" : "查看游戏连接状态"
        dot.font = .systemFont(ofSize: 11); dot.textColor = ConsoleTheme.muted
        let heading = row([label(title, 16, ConsoleTheme.text, .bold), dot], spacing: 8)
        let text = column([heading] + lines, spacing: 6)
        for view in lines { view.setContentCompressionResistancePriority(.defaultLow, for: .horizontal); view.widthAnchor.constraint(equalTo: text.widthAnchor).isActive = true; if let field = view as? NSTextField { field.cell?.wraps = true; field.cell?.usesSingleLineMode = false; field.lineBreakMode = .byWordWrapping } }
        let tile = row([iconButton, text], spacing: 15); tile.alignment = .top
        iconButton.widthAnchor.constraint(equalToConstant: 66).isActive = true; iconButton.heightAnchor.constraint(equalToConstant: 66).isActive = true
        text.widthAnchor.constraint(equalTo: tile.widthAnchor, constant: -81).isActive = true
        text.setContentHuggingPriority(.defaultLow, for: .horizontal)
        return tile
    }
    @objc func stopService() { if backend?.isRunning == true { stopBackend() } }
    @objc func launchOrOpen() { if connection != nil { openMap() } else { startBackend() } }
    @objc func showModInfo() {
        let alert = NSAlert(); alert.messageText = "游戏连接 · 1.4.3"
        alert.informativeText = Self.nativeEdition ? "启动原生王国之泪 1.4.3 后自动连接。游戏启动和键位设置位于主窗口上方。" : "当前维护原生王国之泪 1.4.3，启动游戏后自动连接。模拟器适配尚未实现。"
        alert.addButton(withTitle: "知道了"); alert.runModal()
    }
    @objc func toggleLogDetail() { refreshConsole() }
    func recordEvent(_ key: String, _ message: String) {
        guard eventValues[key] != message else { return }; eventValues[key] = message
        let f = DateFormatter(); f.dateFormat = "HH:mm:ss"
        events.append(f.string(from: Date()) + "  " + message.replacingOccurrences(of: "\n", with: " · ")); if events.count > 100 { events.removeFirst(events.count - 100) }
        if detailedLogs.state != .on { displayLog(events.joined(separator: "\n")) }
    }
    func displayLog(_ text: String) {
        guard logView.string != text else { return }
        let selection = logView.selectedRange()
        let nearBottom = logView.string.isEmpty || logView.visibleRect.maxY >= logView.bounds.height - 30
        logView.string = text
        if selection.length > 0, NSMaxRange(selection) <= (text as NSString).length { logView.setSelectedRange(selection) }
        if nearBottom && selection.length == 0 { logView.scrollToEndOfDocument(nil) }
    }
    func refreshConsole() {
        recordEvent("service", status.stringValue)
        recordEvent("save", progress.stringValue + " · " + saveDate.stringValue)
        recordEvent("mod", telemetryStatus.stringValue)
        recordEvent("mcp", "MCP · " + mcpState.stringValue)
        if connection != nil { recordEvent("phone", "手机入口 · " + phoneAddress.stringValue) }
        if detailedLogs.state != .on { displayLog(events.joined(separator: "\n")); return }
        guard !readingLogs else { return }; readingLogs = true
        let path = logURL; let secrets = [connection?["token"] as? String, settings.string(forKey: "webToken")].compactMap { $0 }
        DispatchQueue.global(qos: .utility).async { [weak self] in
            var text = "暂无详细日志"
            if let file = try? FileHandle(forReadingFrom: path) { defer { try? file.close() }; let end = (try? file.seekToEnd()) ?? 0; try? file.seek(toOffset: end > 65536 ? end - 65536 : 0); if let data = try? file.readToEnd() { text = String(decoding: data, as: UTF8.self) }; for secret in secrets { text = text.replacingOccurrences(of: secret, with: "[redacted]") } }
            DispatchQueue.main.async { guard let self = self else { return }; self.readingLogs = false; if self.detailedLogs.state == .on { self.displayLog(text) } }
        }
    }
    func setReady(_ ready: Bool) {
        mapButton.isEnabled = true; mapButton.title = ready ? "打开地图" : "启动服务"; mapButton.symbol = ready ? "arrow.up.right" : "start"; mapButton.setAccessibilityLabel(mapButton.title); mcpButton.isEnabled = ready; mcpCopyButton.isEnabled = ready; mcpDot.textColor = ready ? ConsoleTheme.mint : ConsoleTheme.muted
        serviceDot.textColor = ready ? ConsoleTheme.mint : ConsoleTheme.muted
        mcpState.stringValue = ready ? "本地 HTTP\n服务已就绪" : "等待服务启动"
        if !ready { networks.isHidden = true; networkAddress.isHidden = false; networkAddress.stringValue = "等待服务启动"; qrPlaceholder.isHidden = false; qrPlaceholder.stringValue = "等待服务启动"; copyButton.isEnabled = false; networks.isEnabled = false; phoneAddress.stringValue = ""; qrHint.stringValue = "服务启动后生成二维码"; saveDot.textColor = ConsoleTheme.muted; modDot.textColor = ConsoleTheme.muted }
    }
    func lanAddresses() -> [String] {
        var list: UnsafeMutablePointer<ifaddrs>?; guard getifaddrs(&list) == 0, let first = list else { return [] }; defer { freeifaddrs(list) }
        var values: [(String, String)] = []; var cursor: UnsafeMutablePointer<ifaddrs>? = first
        while let item = cursor { defer { cursor = item.pointee.ifa_next }; let entry = item.pointee
            guard let address = entry.ifa_addr, address.pointee.sa_family == UInt8(AF_INET), (entry.ifa_flags & UInt32(IFF_UP)) != 0 else { continue }
            let name = String(cString: entry.ifa_name); guard name.hasPrefix("en") || name.hasPrefix("bridge") else { continue }
            var buffer = [CChar](repeating: 0, count: Int(INET_ADDRSTRLEN)); var addr = UnsafeRawPointer(address).assumingMemoryBound(to: sockaddr_in.self).pointee.sin_addr
            guard inet_ntop(AF_INET, &addr, &buffer, socklen_t(INET_ADDRSTRLEN)) != nil else { continue }
            let ip = String(cString: buffer); let parts = ip.split(separator: ".").compactMap { Int($0) }
            guard parts.count == 4, parts[0] == 10 || (parts[0] == 192 && parts[1] == 168) || (parts[0] == 172 && (16...31).contains(parts[1])) else { continue }
            values.append((name, ip))
        }
        return values.sorted { $0.0 < $1.0 }.map { $0.1 }
    }
    @objc func updateQR() {
        guard let urls = connection?["lanURLs"] as? [String], urls.indices.contains(networks.indexOfSelectedItem), let url = URL(string: urls[networks.indexOfSelectedItem]) else { networks.isHidden = true; networkAddress.isHidden = false; networkAddress.stringValue = "暂无局域网地址"; phoneAddress.stringValue = "暂无局域网地址"; qrHint.stringValue = "连接 Wi-Fi 后重新启动服务"; copyButton.isEnabled = false; qrPlaceholder.isHidden = false; qrPlaceholder.stringValue = "暂无局域网连接"; qr.image = nil; return }
        networks.isHidden = urls.count <= 1; networkAddress.isHidden = urls.count > 1; networkAddress.stringValue = url.host ?? "暂无局域网地址"
        copyButton.isEnabled = true; networks.isEnabled = true; qrHint.stringValue = "手机与电脑连接同一 Wi-Fi\n客户端需保持运行"
        phoneAddress.stringValue = "http://" + (url.host ?? "") + ":" + String(url.port ?? 8765)
        let filter = CIFilter(name: "CIQRCodeGenerator")!; filter.setValue(Data(url.absoluteString.utf8), forKey: "inputMessage"); filter.setValue("M", forKey: "inputCorrectionLevel")
        guard let output = filter.outputImage else { return }
        let extent = output.extent.insetBy(dx: -4, dy: -4); let factor = floor(496 / extent.width)
        let background = CIImage(color: CIColor.white).cropped(to: extent); let image = output.composited(over: background).transformed(by: CGAffineTransform(scaleX: factor, y: factor))
        if let bitmap = CIContext().createCGImage(image, from: image.extent) { qr.image = NSImage(cgImage: bitmap, size: NSSize(width: image.extent.width / 2, height: image.extent.height / 2)); qrPlaceholder.isHidden = true }
    }
    @objc func openMap() { if let text = connection?["url"] as? String, let url = URL(string: text) { NSWorkspace.shared.open(url) } }
    @objc func copyPhone() { guard let urls = connection?["lanURLs"] as? [String], urls.indices.contains(networks.indexOfSelectedItem) else { return }; NSPasteboard.general.clearContents(); NSPasteboard.general.setString(urls[networks.indexOfSelectedItem], forType: .string); feedback.stringValue = "手机链接已复制" }
    @objc func toggleService() { if backend?.isRunning == true { stopBackend(); connection = nil; window.subtitle = "" } else { startBackend() } }
    func pollTelemetry() {
        guard let child = backend, let base = connection?["url"] as? String, let url = URL(string: base + "api/position") else { return }
        URLSession.shared.dataTask(with: url) { [weak self] data, _, _ in
            guard let data = data, let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
            DispatchQueue.main.async { guard let self = self, self.backend === child else { return }
                if json["modConnected"] as? Bool == true {
                    self.modDot.textColor = ConsoleTheme.mint
                    self.telemetryStatus.stringValue = "实时位置已启用 · " + ((json["headingAvailable"] as? Bool == true) ? "朝向已启用" : "朝向尚未验证")
                } else if json["available"] as? Bool == true {
                    self.modDot.textColor = ConsoleTheme.gold; self.telemetryStatus.stringValue = "内存备用位置 · 等待游戏启动"
                } else { self.modDot.textColor = ConsoleTheme.muted; self.telemetryStatus.stringValue = Self.nativeEdition ? (json["error"] as? String ?? "等待游戏启动\n请进入游戏场景") : "等待游戏启动\n请进入游戏场景" }
            }
        }.resume()
    }
    func pollProgress() {
        pollTelemetry()
        tunnelRequest()
        guard let child = backend, let base = connection?["url"] as? String, let url = URL(string: base + "api/progress") else { return }
        URLSession.shared.dataTask(with: url) { [weak self] data, _, _ in
            guard let data = data, let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
            DispatchQueue.main.async { guard let self = self, self.backend === child else { return }
                if let error = json["error"] as? String { self.saveDot.textColor = ConsoleTheme.gold; self.progress.stringValue = error; self.saveDate.stringValue = "可选择目录，或恢复自动查找" }
                else {
                    self.saveDot.textColor = ConsoleTheme.mint
                    self.progress.stringValue = "已同步 · \(json["completedPoints"] ?? 0) 个点位"
                    self.progress.toolTip = "\(json["slots"] ?? 0) 个有效存档槽 · 监测文件变更，自动读取最新有效存档"
                    self.saveDate.stringValue = "监测文件变更，自动读取最新存档"
                    if let ms = json["mtime"] as? Double { let f = DateFormatter(); f.dateFormat = "M月d日 HH:mm:ss"; self.saveDate.stringValue = "最新存档\n" + f.string(from: Date(timeIntervalSince1970: ms / 1000)) }
                }
            }
        }.resume()
    }
    func makeMenu() {
        let menu = NSMenu()
        let appItem = NSMenuItem()
        let appMenu = NSMenu(title: "王国之泪")
        appMenu.addItem(withTitle: "关于王国之泪离线地图", action: #selector(about), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "退出", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        menu.addItem(appItem)
        let serviceItem = NSMenuItem()
        let serviceMenu = NSMenu(title: "服务")
        serviceMenu.addItem(withTitle: "导入数据包…", action: #selector(importDataPacks), keyEquivalent: "i")
        serviceMenu.addItem(withTitle: "已安装数据包…", action: #selector(showDataPackInfo), keyEquivalent: "")
        serviceMenu.addItem(withTitle: "打开数据包目录", action: #selector(showDataPacks), keyEquivalent: "")
        serviceMenu.addItem(withTitle: "查看游戏连接状态…", action: #selector(showModInfo), keyEquivalent: "")
        serviceMenu.addItem(withTitle: "MCP 连接信息…", action: #selector(showMCP), keyEquivalent: "m")
        serviceMenu.addItem(withTitle: "固定地址 MCP 隧道…", action: #selector(showTunnelSettings), keyEquivalent: "")
        serviceMenu.addItem(withTitle: "复制远程 MCP 配置", action: #selector(copyRemoteMCP), keyEquivalent: "")
        serviceMenu.addItem(withTitle: "复制 MCP 配置", action: #selector(copyMCP), keyEquivalent: "")
        serviceMenu.addItem(.separator())
        serviceMenu.addItem(withTitle: "选择存档目录…", action: #selector(chooseSave), keyEquivalent: "o")
        serviceMenu.addItem(withTitle: "恢复自动查找存档", action: #selector(resetSave), keyEquivalent: "")
        serviceMenu.addItem(withTitle: "停止／启动服务", action: #selector(toggleService), keyEquivalent: "")

        serviceMenu.addItem(withTitle: "重新启动服务", action: #selector(restart), keyEquivalent: "r")
        serviceMenu.addItem(withTitle: "查看服务日志", action: #selector(showLog), keyEquivalent: "")
        serviceItem.submenu = serviceMenu
        menu.addItem(serviceItem)
        let editItem = NSMenuItem()
        let edit = NSMenu(title: "编辑")
        edit.addItem(withTitle: "撤销", action: Selector(("undo:")), keyEquivalent: "z")
        edit.addItem(withTitle: "剪切", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        edit.addItem(withTitle: "复制", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "粘贴", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "全选", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = edit
        menu.addItem(editItem)
        for item in appMenu.items + serviceMenu.items where item.action != #selector(NSApplication.terminate(_:)) { item.target = self }
        NSApp.mainMenu = menu
    }
    func startBackend() {
        feedback.stringValue = "客户端保持运行，地图与同步服务即可持续使用。"
        stopBackend()
        connection = nil
        setReady(false); mapButton.isEnabled = false; mapButton.title = "正在启动…"; window.subtitle = ""; serviceDot.textColor = ConsoleTheme.gold; serviceButton.title = "正在启动"; serviceButton.isEnabled = false
        status.stringValue = "正在启动服务…"
        telemetryStatus.stringValue = "等待游戏启动"
        localAddress.stringValue = "本地地图与 MCP 服务正在准备"
        progress.stringValue = "等待存档同步"
        qr.image = nil
        do {
            try FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
            try? FileManager.default.removeItem(at: runtime)
            let executable = Bundle.main.resourceURL!.appendingPathComponent("backend/totk-service")
            guard FileManager.default.isExecutableFile(atPath: executable.path) else { throw NSError(domain: "TOTK", code: 1, userInfo: [NSLocalizedDescriptionKey: "缺少内置服务程序"] ) }
            let child = Process()
            child.executableURL = executable
            var arguments = ["--lan", "--port", Self.nativeEdition ? "8766" : "8765", "--fallback-port", "--runtime-file", runtime.path, "--parent-pid", String(ProcessInfo.processInfo.processIdentifier)]
            if let root = settings.string(forKey: "saveDirectory") { arguments += ["--save-dir", root] }
            child.arguments = arguments
            var environment = ProcessInfo.processInfo.environment
            var token = settings.string(forKey: "mcpToken")
            if token == nil { token = UUID().uuidString + UUID().uuidString; settings.set(token, forKey: "mcpToken") }
            environment["TOTK_MCP_TOKEN"] = token
            environment["TOTK_RESOURCE_ROOT"] = Bundle.main.resourceURL!.path
            environment["TOTK_SUPPORT_ROOT"] = support.path
            if Self.nativeEdition {
                environment["TOTK_CLIENT_EDITION"] = "native"
                environment["TOTK_DATA_SUPPORT_ROOT"] = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("TOTK Offline").path
            }
            environment["TOTK_TILE_CACHE"] = support.appendingPathComponent("tiles", isDirectory: true).path
            environment["TOTK_LAN_HOSTS"] = lanAddresses().joined(separator: ",")
            var webToken = settings.string(forKey: "webToken")
            if webToken == nil { webToken = UUID().uuidString + UUID().uuidString; settings.set(webToken, forKey: "webToken") }
            environment["TOTK_WEB_TOKEN"] = webToken
            child.environment = environment
            FileManager.default.createFile(atPath: logURL.path, contents: nil)
            let log = try FileHandle(forWritingTo: logURL)
            child.standardOutput = log
            child.standardError = log
            try child.run()
            backend = child
            startingAt = Date()
            timer = Timer.scheduledTimer(withTimeInterval: 0.2, repeats: true) { [weak self] _ in self?.checkReady() }
        } catch { fail(error.localizedDescription) }
    }
    func checkReady() {
        guard let child = backend else { return }
        if !child.isRunning { timer?.invalidate(); fail("内置服务已退出。\n" + ((try? String(contentsOf: logURL, encoding: .utf8)) ?? "")); return }
        if let data = try? Data(contentsOf: runtime), let info = try? JSONSerialization.jsonObject(with: data) as? [String: Any], (info["pid"] as? Int) == Int(child.processIdentifier), let address = info["url"] as? String, URL(string: address) != nil {
            connection = info
            timer?.invalidate()
            localAddress.stringValue = address
            status.stringValue = (info["offlineMap"] as? [String: Any])?["complete"] as? Bool == true ? "离线地图已就绪" : "请导入地图数据包"
            serviceButton.title = "停止服务"; serviceButton.symbol = "stop"; serviceButton.isEnabled = true; setReady(true)
            let links = info["lanURLs"] as? [String] ?? []
            networks.removeAllItems(); networks.addItems(withTitles: links.compactMap { URL(string: $0)?.host }); updateQR()
            restoreTunnel()
            pollProgress()
            progressTimer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in self?.pollProgress() }
            // The map opens only through the explicit Open Map action.
            window.subtitle = ""
            child.terminationHandler = { [weak self] process in
                DispatchQueue.main.async {
                    guard let self = self, self.backend === process else { return }
                    self.setReady(false); self.connection = nil; self.window.subtitle = ""; self.status.stringValue = "服务已停止"; self.telemetryStatus.stringValue = "遥测监听已停止"; self.qr.image = nil; self.serviceButton.title = "启动服务"; self.progressTimer?.invalidate()
                }
            }
        } else if Date().timeIntervalSince(startingAt) > 30 { timer?.invalidate(); stopBackend(); fail("启动服务超时，请查看服务日志。") }
    }
    func stopBackend() {
        timer?.invalidate()
        progressTimer?.invalidate()
        tunnelInfo = [:]; tunnelRequestRunning = false; pendingTunnelRequest = nil
        setReady(false); connection = nil; status.stringValue = "服务已停止"
        telemetryStatus.stringValue = "启动服务后监听游戏"; progress.stringValue = "存档同步已暂停"; saveDate.stringValue = "启动服务后自动恢复"; localAddress.stringValue = "点击启动服务，继续探索"
        serviceButton.title = "启动服务"; serviceButton.symbol = "start"; serviceButton.isEnabled = true
        qr.image = nil
        let child = backend
        backend = nil
        child?.terminationHandler = nil
        if child?.isRunning == true { child?.terminate(); child?.waitUntilExit() }
        try? FileManager.default.removeItem(at: runtime)
    }
    func fail(_ message: String) {
        setReady(false); serviceButton.isEnabled = true; serviceButton.title = "启动服务"; serviceButton.symbol = "start"; status.stringValue = "服务启动失败"; serviceDot.textColor = .systemRed; window.subtitle = ""
        let alert = NSAlert(); alert.messageText = "服务启动失败"; alert.informativeText = String(message.suffix(4000)); alert.addButton(withTitle: "重试"); alert.addButton(withTitle: "关闭")
        if alert.runModal() == .alertFirstButtonReturn { startBackend() }
    }
    func mcpConfig(remote: Bool = false) -> String? {
        guard let connection = connection, let localURL = connection["mcpURL"] as? String, let token = connection["token"] as? String else { return nil }
        guard let url = remote ? (tunnelInfo["state"] as? String == "connected" ? tunnelInfo["url"] as? String : nil) : localURL else { return nil }
        let object: [String: Any] = ["mcpServers": ["totk-offline": ["url": url, "headers": remote ? ["Authorization": "Bearer " + token, "ngrok-skip-browser-warning": "1"] : ["Authorization": "Bearer " + token]]]]
        return (try? JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])).flatMap { String(data: $0, encoding: .utf8) }
    }
    @objc func showMCP() {
        guard let text = mcpConfig() else { feedback.stringValue = "请先启动服务，再查看 MCP 配置"; return }
        let alert = NSAlert(); alert.messageText = "MCP 服务已启动"; alert.informativeText = "本地 Streamable HTTP 服务。将下面的连接配置导入支持 HTTP MCP 的客户端。应用退出后服务停止。"; alert.addButton(withTitle: "复制本地配置"); alert.addButton(withTitle: "关闭"); alert.addButton(withTitle: "固定隧道…")
        let scroll = NSScrollView(frame: NSRect(x: 0, y: 0, width: 540, height: 180)); scroll.hasVerticalScroller = true
        let view = NSTextView(frame: scroll.bounds); view.isEditable = false; view.isSelectable = true; view.font = NSFont.monospacedSystemFont(ofSize: 12, weight: .regular); view.string = text; scroll.documentView = view; alert.accessoryView = scroll
        let result = alert.runModal(); if result == .alertFirstButtonReturn { copyMCP() }; if result == .alertThirdButtonReturn { showTunnelSettings() }
    }
    @objc func copyMCP() { if let text = mcpConfig() { NSPasteboard.general.clearContents(); NSPasteboard.general.setString(text, forType: .string); feedback.stringValue = "MCP 连接配置已复制" } else { feedback.stringValue = "请先启动服务，再复制 MCP 配置" } }
    @objc func chooseSave() {
        let panel = NSOpenPanel(); panel.canChooseDirectories = true; panel.canChooseFiles = false; panel.allowsMultipleSelection = false; panel.message = "选择包含 progress.sav 的目录，将递归查找最新有效存档。"
        if panel.runModal() == .OK, let url = panel.url { settings.set(url.path, forKey: "saveDirectory"); startBackend() }
    }
    @objc func resetSave() { settings.removeObject(forKey: "saveDirectory"); startBackend() }
    @objc func restart() { startBackend() }
    @objc func showLog() { NSWorkspace.shared.open(logURL) }
    @objc func about() { let alert = NSAlert(); alert.messageText = "王国之泪 · 离线地图"; alert.informativeText = "离线地图和攻略 · 自动读取最新存档 · 本地 MCP\n存档解析只读；游戏控制通过游戏执行。"; alert.runModal() }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationWillTerminate(_ notification: Notification) { consoleTimer?.invalidate(); stopBackend() }
}
