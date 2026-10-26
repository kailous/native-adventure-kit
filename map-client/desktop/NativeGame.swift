import AppKit
import UniformTypeIdentifiers

struct InputAction: Decodable { let id: String; let label: String; let keys: [Int] }
struct InputSchema: Decodable { let schema: Int; let actions: [InputAction] }
struct InputConfigError: LocalizedError { let message: String; var errorDescription: String? { message } }

// The schema is shipped by the independently maintained native game repository.
struct NativeBindings {
    let actions: [InputAction]
    var keys: [[Int]]
    var mouse: [String]
    var controller: [String]
    let directory: URL
    var originalKeyboard: Data?
    var originalControls: Data?
    var controlComments: [String:String] = [:]
    static let controllerNames = ["south", "east", "west", "north", "l3", "r3", "l1", "r1", "l2", "r2", "menu", "view", "left", "up", "right", "down", "touchpad"]
    static let controllerLabels = ["下方面键 · A / × / B", "右方面键 · B / ○ / A", "左方面键 · X / □ / Y", "上方面键 · Y / △ / X", "左摇杆按下 · L3", "右摇杆按下 · R3", "左肩键 · LB / L1 / L", "右肩键 · RB / R1 / R", "左扳机 · LT / L2 / ZL", "右扳机 · RT / R2 / ZR", "菜单 · Start / Options / ＋", "视图 · Back / Share / －", "方向键：左", "方向键：上", "方向键：右", "方向键：下", "触摸板按下"]
    static let controllerDefaults = ["b", "a", "y", "x", "lstick", "rstick", "l", "r", "zl", "zr", "plus", "minus", "left", "up", "right", "down", "none"]
    static let mouseNames = ["mouse_left", "mouse_right", "mouse_middle", "mouse4", "mouse5"]
    static let mouseLabels = ["鼠标左键", "鼠标右键", "鼠标中键", "鼠标侧键 1", "鼠标侧键 2"]
    static let mouseDefaults = ["y", "zr aim mouse_left", "zl", "none", "none"]
    static let targets = ["none", "a", "b", "x", "y", "lstick", "rstick", "l", "r", "zl", "zr", "plus", "minus", "left", "up", "right", "down", "zr aim mouse_left"]
    static let targetLabels = ["不使用", "A · 互动", "B · 冲刺", "X · 跳跃", "Y · 攻击", "左摇杆 · 蹲下", "右摇杆 · 望远镜", "L · 能力", "R · 投掷", "ZL · 锁定", "ZR · 举弓", "＋ · 暂停", "－ · 地图", "方向键左", "方向键上", "方向键右", "方向键下", "举弓，左键射箭"]
    init(directory: URL, schemaURL: URL) throws {
        let schema = try JSONDecoder().decode(InputSchema.self, from: Data(contentsOf: schemaURL))
        guard schema.schema == 1, schema.actions.count == 25, Set(schema.actions.map(\.id)).count == 25 else { throw InputConfigError(message: "键位定义无效，请重新安装客户端。") }
        self.directory = directory; actions = schema.actions; keys = actions.map(\.keys); mouse = Self.mouseDefaults; controller = Self.controllerDefaults
        originalKeyboard = try Self.read(directory.appendingPathComponent("keyboard.txt"))
        originalControls = try Self.read(directory.appendingPathComponent("controls.txt"))
        if let data = originalKeyboard {
            guard let text = String(data: data, encoding: .utf8) else { throw InputConfigError(message: "keyboard.txt 不是 UTF-8 文本。") }
            var seen = Set<String>()
            for line in text.components(separatedBy: .newlines) {
                let part = line.components(separatedBy: "#")[0].trimmingCharacters(in: .whitespaces)
                if part.isEmpty { continue }
                let pair = part.components(separatedBy: "=").map { $0.trimmingCharacters(in: .whitespaces) }
                guard pair.count == 2, let index = actions.firstIndex(where: { $0.id == pair[0] }), seen.insert(pair[0]).inserted else { throw InputConfigError(message: "keyboard.txt 有未知或重复的动作，请先修正文件。") }
                if pair[1] == "none" { keys[index] = [] }
                else {
                    let codes = pair[1].components(separatedBy: ",").map { Int($0.trimmingCharacters(in: .whitespaces)) }
                    guard !codes.isEmpty, codes.count <= 4, codes.allSatisfy({ $0 != nil && (0..<128).contains($0!) }) else { throw InputConfigError(message: "keyboard.txt 的按键编号无效。") }
                    keys[index] = codes.map { $0! }
                }
            }
        }
        if let data = originalControls {
            guard let text = String(data: data, encoding: .utf8) else { throw InputConfigError(message: "controls.txt 不是 UTF-8 文本。") }
            for line in text.components(separatedBy: .newlines) {
                let part = line.components(separatedBy: "#")[0]
                let pair = part.components(separatedBy: "=").map { $0.trimmingCharacters(in: .whitespaces).lowercased() }
                if part.trimmingCharacters(in: .whitespaces).isEmpty { continue }
                guard pair.count == 2, (Self.controllerNames + Self.mouseNames).contains(pair[0]) else { throw InputConfigError(message: "controls.txt 包含未知按键或无效配置，原文件已保留。") }
                if let hash = line.firstIndex(of: "#") { controlComments[pair[0]] = String(line[hash...]) }
                if pair.count == 2 {
                    if let index = Self.mouseNames.firstIndex(of: pair[0]) { mouse[index] = pair[1] }
                    if let index = Self.controllerNames.firstIndex(of: pair[0]) { controller[index] = pair[1] }
                }
            }
        }
        if let problem = validation { throw InputConfigError(message: problem) }
    }
    static func read(_ url: URL) throws -> Data? {
        guard FileManager.default.fileExists(atPath: url.path) else { return nil }
        let data = try Data(contentsOf: url)
        guard data.count < 16384, !data.contains(0) else { throw InputConfigError(message: "键位文件过大或包含无效字符。原文件已保留。") }
        return data
    }
    var validation: String? {
        var used = Set<Int>()
        for (index, codes) in keys.enumerated() {
            guard codes.count <= 4 else { return actions[index].label + "：最多设置 4 个按键。" }
            for code in codes { if !(0..<128).contains(code) || !used.insert(code).inserted { return "按键重复：" + Self.keyName(code) + "。请先清除另一个动作的绑定。" } }
        }
        for (name, value) in zip(Self.controllerNames + Self.mouseNames, controller + mouse) {
            if !Self.validControl(value, physical: name) { return "按键配置无效：" + name + "。请检查目标动作与触发方式。" }
        }
        return nil
    }
    static func validControl(_ value: String, physical: String) -> Bool {
        let words = value.split(whereSeparator: { $0.isWhitespace }).map(String.init)
        guard let target = words.first, Self.targets.prefix(17).contains(target) else { return false }
        if words.count == 1 { return true }
        guard target != "none" else { return false }
        if words.count == 2 { return ["hold", "tap", "toggle"].contains(words[1]) }
        return words.count == 3 && words[1] == "aim" && (controllerNames + mouseNames).contains(words[2]) && words[2] != physical
    }
    mutating func setControllerTarget(_ target: String, at index: Int) {
        let words = controller[index].split(whereSeparator: { $0.isWhitespace })
        let mode = words.dropFirst().joined(separator: " ")
        controller[index] = target + (target == "none" || mode.isEmpty ? "" : " " + mode)
    }
    static func controllerModeLabel(_ value: String) -> String {
        let words = value.split(whereSeparator: { $0.isWhitespace })
        guard words.count > 1 else { return "按住" }
        switch words[1] {
        case "hold": return "按住"
        case "tap": return "点按 · 400 ms"
        case "toggle": return "按下切换"
        case "aim":
            let fire = words.count > 2 ? String(words[2]) : ""
            let label = controllerNames.firstIndex(of: fire).map { controllerLabels[$0] } ?? fire
            return "瞄准；射击键：" + label
        default: return "保留模式：" + words.dropFirst().joined(separator: " ")
        }
    }
    mutating func save() throws {
        if let problem = validation { throw InputConfigError(message: problem) }
        let keyboardURL = directory.appendingPathComponent("keyboard.txt"), controlsURL = directory.appendingPathComponent("controls.txt")
        guard try Self.read(keyboardURL) == originalKeyboard, try Self.read(controlsURL) == originalControls else { throw InputConfigError(message: "键位文件已被其他程序修改，请关闭此窗口后重新打开。") }
        let keyboard = "# Native TOTK keyboard configuration v1\n" + actions.enumerated().map { index, action in action.id + " = " + (keys[index].isEmpty ? "none" : keys[index].map(String.init).joined(separator: ",")) }.joined(separator: "\n") + "\n"
        // Preserve comments and unrelated lines; edit controller and mouse rows together.
        var controls = String(data: originalControls ?? Data(), encoding: .utf8)!.components(separatedBy: .newlines).filter { line in
            if ["# Controller buttons", "# Mouse buttons"].contains(line.trimmingCharacters(in: .whitespaces)) { return false }
            let key = line.components(separatedBy: "#")[0].components(separatedBy: "=")[0].trimmingCharacters(in: .whitespaces).lowercased()
            return !Self.mouseNames.contains(key) && !Self.controllerNames.contains(key)
        }.joined(separator: "\n").trimmingCharacters(in: .newlines)
        controls += "\n# Controller buttons\n" + Self.controllerNames.enumerated().map { $0.element + " = " + controller[$0.offset] + (controlComments[$0.element].map { " " + $0 } ?? "") }.joined(separator: "\n") + "\n"
        controls += "\n# Mouse buttons\n" + Self.mouseNames.enumerated().map { $0.element + " = " + mouse[$0.offset] + (controlComments[$0.element].map { " " + $0 } ?? "") }.joined(separator: "\n") + "\n"
        let keyboardData = Data(keyboard.utf8), controlsData = Data(controls.utf8)
        guard controlsData.count < 16384 else { throw InputConfigError(message: "controls.txt 将超过 16 KB，未保存。") }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try keyboardData.write(to: keyboardURL, options: .atomic)
        do { try controlsData.write(to: controlsURL, options: .atomic) }
        catch {
            if let originalKeyboard = originalKeyboard { try originalKeyboard.write(to: keyboardURL, options: .atomic) }
            else { try FileManager.default.removeItem(at: keyboardURL) }
            throw error
        }
        originalKeyboard = keyboardData; originalControls = controlsData
    }
    static func keyName(_ code: Int) -> String {
        let known: [Int:String] = [0:"A",1:"S",2:"D",3:"F",4:"H",5:"G",6:"Z",7:"X",8:"C",9:"V",11:"B",12:"Q",13:"W",14:"E",15:"R",16:"Y",17:"T",18:"1",19:"2",20:"3",21:"4",22:"6",23:"5",24:"=",25:"9",26:"7",27:"−",28:"8",29:"0",30:"]",31:"O",32:"U",33:"[",34:"I",35:"P",36:"Return",37:"L",38:"J",39:"'",40:"K",41:";",42:"\\",43:",",44:"/",45:"N",46:"M",47:".",48:"Tab",49:"Space",50:"`",51:"Delete",53:"Esc",54:"右 ⌘",55:"⌘",56:"Shift",57:"Caps Lock",58:"Option",59:"Control",60:"右 Shift",61:"右 Option",62:"右 Control",63:"Fn",96:"F5",97:"F6",98:"F7",99:"F3",100:"F8",101:"F9",103:"F11",109:"F10",111:"F12",115:"Home",116:"Page Up",117:"向前删除",118:"F4",119:"End",120:"F2",121:"Page Down",122:"F1",123:"←",124:"→",125:"↓",126:"↑"]
        return known[code] ?? "按键 \(code)"
    }
}

final class BindingRows: NSStackView { override var isFlipped: Bool { true } }

final class KeyCaptureButton: ConsoleButton {
    var capture: ((Int) -> Void)?
    var recording = false
    override var acceptsFirstResponder: Bool { true }
    override func keyDown(with event: NSEvent) { if recording { capture?(Int(event.keyCode)) } else { super.keyDown(with: event) } }
    override func flagsChanged(with event: NSEvent) {
        let flags: [UInt16:NSEvent.ModifierFlags] = [54:.command,55:.command,56:.shift,60:.shift,58:.option,61:.option,59:.control,62:.control,57:.capsLock,63:.function]
        if recording, let flag = flags[event.keyCode], event.modifierFlags.contains(flag) { capture?(Int(event.keyCode)) }
        else { super.flagsChanged(with: event) }
    }
}

final class KeyBindingsWindow: NSWindowController {
    var bindings: NativeBindings
    var buttons: [KeyCaptureButton] = []
    var mouseMenus: [NSPopUpButton] = []
    var controllerMenus: [NSPopUpButton] = []
    var controllerHints: [NSTextField] = []
    var deviceGroups: [BindingRows] = []
    let devicePicker = NSSegmentedControl(labels: ["键盘", "鼠标", "手柄"], trackingMode: .selectOne, target: nil, action: nil)
    weak var bindingsScroll: NSScrollView?
    let message = NSTextField(wrappingLabelWithString: "")
    let saveButton = ConsoleButton(title: "保存键位", target: nil, action: nil)
    init(bindings: NativeBindings) {
        self.bindings = bindings
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 620, height: 690), styleMask: [.titled, .closable], backing: .buffered, defer: false)
        super.init(window: window); window.contentView?.wantsLayer = true; window.contentView?.layer?.backgroundColor = ConsoleTheme.surface.cgColor; window.title = "游戏键位"; window.appearance = NSAppearance(named: .darkAqua); window.backgroundColor = ConsoleTheme.surface; window.isReleasedWhenClosed = false
        let root = NSStackView(); root.orientation = .vertical; root.spacing = 14; root.alignment = .leading
        window.contentView!.addSubview(root); root.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([root.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor, constant: 24), root.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor, constant: -24), root.topAnchor.constraint(equalTo: window.contentView!.topAnchor, constant: 20), root.bottomAnchor.constraint(equalTo: window.contentView!.bottomAnchor, constant: -20)])
        let title = NSTextField(labelWithString: "按你的习惯，探索海拉鲁"); title.font = .systemFont(ofSize: 22, weight: .bold); title.textColor = ConsoleTheme.text
        let hint = NSTextField(wrappingLabelWithString: "键盘点击录入，鼠标与手柄选择目标动作。\n保存后下次启动游戏生效，不会修改游戏存档。"); hint.font = .systemFont(ofSize: 12); hint.textColor = ConsoleTheme.muted
        root.addArrangedSubview(title); root.addArrangedSubview(hint)
        devicePicker.selectedSegment = 0; devicePicker.target = self; devicePicker.action = #selector(changeDevice)
        root.addArrangedSubview(devicePicker)
        let scroll = NSScrollView(); scroll.hasVerticalScroller = true; scroll.drawsBackground = false
        bindingsScroll = scroll
        let rows = BindingRows(); rows.orientation = .vertical; rows.alignment = .leading; rows.spacing = 8; scroll.documentView = rows; rows.translatesAutoresizingMaskIntoConstraints = false
        root.addArrangedSubview(scroll); scroll.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        rows.widthAnchor.constraint(equalTo: scroll.contentView.widthAnchor, constant: -12).isActive = true
        for device in 0..<3 {
            let group = BindingRows(); group.orientation = .vertical; group.alignment = .leading; group.spacing = 8
            rows.addArrangedSubview(group); group.widthAnchor.constraint(equalTo: rows.widthAnchor).isActive = true
            group.isHidden = device != 0; deviceGroups.append(group)
        }
        let keyboardRows = deviceGroups[0], mouseRows = deviceGroups[1], controllerRows = deviceGroups[2]
        for (index, action) in bindings.actions.enumerated() {
            if [0,16,20,24].contains(index) { let section = NSTextField(labelWithString: index == 0 ? "动作" : index == 16 ? "移动" : index == 20 ? "视角" : "鼠标模式"); section.textColor = ConsoleTheme.gold; section.font = .systemFont(ofSize: 13, weight: .semibold); keyboardRows.addArrangedSubview(section) }
            let label = NSTextField(labelWithString: action.label); label.font = .systemFont(ofSize: 13)
            let button = KeyCaptureButton(title: "", target: nil, action: nil); button.controlHeight = 32; button.tag = index; button.target = self; button.action = #selector(record(_:)); button.bezelStyle = .rounded; button.setAccessibilityLabel(action.label + "绑定按键")
            button.capture = { [weak self, weak button] code in guard let self = self, let button = button else { return }; self.bindings.keys[index] = [code]; button.recording = false; self.refresh() }
            buttons.append(button)
            let clear = ConsoleButton(title: "清除", target: self, action: #selector(clearKey(_:))); clear.controlHeight = 32; clear.tag = index; clear.bezelStyle = .rounded
            let row = NSStackView(views: [label, NSView(), button, clear]); row.spacing = 8; keyboardRows.addArrangedSubview(row); row.widthAnchor.constraint(equalTo: keyboardRows.widthAnchor).isActive = true; button.widthAnchor.constraint(equalToConstant: 155).isActive = true
        }
        let heading = NSTextField(labelWithString: "鼠标按键 · 开启鼠标模式后生效"); heading.textColor = ConsoleTheme.gold; mouseRows.addArrangedSubview(heading)
        for index in 0..<5 {
            let menu = ConsoleNetworkPicker(frame: .zero, pullsDown: false); menu.setAccessibilityLabel(NativeBindings.mouseLabels[index]); menu.tag = index; menu.target = self; menu.action = #selector(mouseChanged(_:))
            menu.addItems(withTitles: NativeBindings.targetLabels)
            if !NativeBindings.targets.contains(bindings.mouse[index]) { menu.addItem(withTitle: "保留自定义：" + bindings.mouse[index]) }
            menu.selectItem(at: NativeBindings.targets.firstIndex(of: bindings.mouse[index]) ?? NativeBindings.targets.count); mouseMenus.append(menu)
            let row = NSStackView(views: [NSTextField(labelWithString: NativeBindings.mouseLabels[index]), NSView(), menu]); mouseRows.addArrangedSubview(row); row.widthAnchor.constraint(equalTo: mouseRows.widthAnchor).isActive = true; menu.widthAnchor.constraint(equalToConstant: 240).isActive = true
        }
        let controllerHeading = NSTextField(wrappingLabelWithString: "按键按物理位置识别，面键名称依次为 Xbox / PlayStation / Switch。\n面键映射用于游戏内“自定义”布局；保留原触发方式和摇杆方向。")
        controllerHeading.font = .systemFont(ofSize: 12); controllerHeading.textColor = ConsoleTheme.muted
        controllerRows.addArrangedSubview(controllerHeading); controllerHeading.widthAnchor.constraint(equalTo: controllerRows.widthAnchor).isActive = true
        for index in NativeBindings.controllerNames.indices {
            let menu = ConsoleNetworkPicker(frame: .zero, pullsDown: false); menu.tag = index; menu.target = self; menu.action = #selector(controllerChanged(_:))
            menu.addItems(withTitles: Array(NativeBindings.targetLabels.prefix(17))); menu.setAccessibilityLabel(NativeBindings.controllerLabels[index] + "映射")
            let hint = NSTextField(wrappingLabelWithString: ""); hint.font = .systemFont(ofSize: 11); hint.textColor = ConsoleTheme.muted
            let choices = NSStackView(views: [menu, hint]); choices.orientation = .vertical; choices.alignment = .leading; choices.spacing = 2
            let label = NSTextField(labelWithString: NativeBindings.controllerLabels[index]); label.font = .systemFont(ofSize: 12)
            let row = NSStackView(views: [label, NSView(), choices]); row.spacing = 8
            controllerRows.addArrangedSubview(row); row.widthAnchor.constraint(equalTo: controllerRows.widthAnchor).isActive = true
            menu.widthAnchor.constraint(equalToConstant: 220).isActive = true; hint.widthAnchor.constraint(equalTo: menu.widthAnchor).isActive = true
            controllerMenus.append(menu); controllerHints.append(hint)
        }
        message.font = .systemFont(ofSize: 12); message.maximumNumberOfLines = 3; root.addArrangedSubview(message); message.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        let reset = ConsoleButton(title: "恢复全部默认", target: self, action: #selector(resetBindings)); reset.bezelStyle = .rounded
        let cancel = ConsoleButton(title: "关闭", target: self, action: #selector(closeEditor)); cancel.bezelStyle = .rounded
        saveButton.target = self; saveButton.action = #selector(saveBindings); saveButton.bezelStyle = .rounded
        let footer = NSStackView(views: [reset, NSView(), cancel, saveButton]); root.addArrangedSubview(footer); footer.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        refresh(); window.contentView?.layoutSubtreeIfNeeded(); rows.scroll(NSPoint(x: 0, y: 0)); window.center()
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    func refresh() {
        for (index, button) in buttons.enumerated() { button.title = button.recording ? "请按下新按键…" : bindings.keys[index].isEmpty ? "未绑定" : bindings.keys[index].map(NativeBindings.keyName).joined(separator: " / ") }
        for (index, menu) in controllerMenus.enumerated() {
            let target = bindings.controller[index].split(whereSeparator: { $0.isWhitespace }).first.map(String.init) ?? "none"
            menu.selectItem(at: NativeBindings.targets.prefix(17).firstIndex(of: target) ?? 0)
            controllerHints[index].stringValue = target == "none" ? "不使用" : NativeBindings.controllerModeLabel(bindings.controller[index])
        }
        let help = devicePicker.selectedSegment == 2 ? "可将多个手柄按键映射到同一动作；选择“不使用”即可清除。" : devicePicker.selectedSegment == 1 ? "鼠标右键默认举弓、左键射箭。" : "可以绑定 Shift、Option 等单个修饰键。"
        message.stringValue = bindings.validation ?? help
        message.textColor = bindings.validation == nil ? ConsoleTheme.muted : .systemOrange; saveButton.isEnabled = bindings.validation == nil
    }
    @objc func changeDevice() {
        buttons.forEach { $0.recording = false }
        for (index, group) in deviceGroups.enumerated() { group.isHidden = index != devicePicker.selectedSegment }
        window?.contentView?.layoutSubtreeIfNeeded(); bindingsScroll?.documentView?.scroll(.zero); refresh()
    }
    @objc func controllerChanged(_ sender: NSPopUpButton) {
        guard (0..<17).contains(sender.indexOfSelectedItem) else { return }
        bindings.setControllerTarget(NativeBindings.targets[sender.indexOfSelectedItem], at: sender.tag); refresh()
    }
    @objc func record(_ sender: KeyCaptureButton) { for button in buttons { button.recording = button === sender }; refresh(); window?.makeFirstResponder(sender) }
    @objc func clearKey(_ sender: NSButton) { buttons.forEach { $0.recording = false }; bindings.keys[sender.tag] = []; refresh() }
    @objc func mouseChanged(_ sender: NSPopUpButton) { if sender.indexOfSelectedItem < NativeBindings.targets.count { bindings.mouse[sender.tag] = NativeBindings.targets[sender.indexOfSelectedItem] }; refresh() }
    @objc func resetBindings() { bindings.keys = bindings.actions.map(\.keys); bindings.mouse = NativeBindings.mouseDefaults; bindings.controller = NativeBindings.controllerDefaults; for (index, menu) in mouseMenus.enumerated() { menu.selectItem(at: NativeBindings.targets.firstIndex(of: bindings.mouse[index])!) }; buttons.forEach { $0.recording = false }; refresh() }
    @objc func closeEditor() { close() }
    @objc func saveBindings() { do { try bindings.save(); buttons.forEach { $0.recording = false }; refresh(); message.stringValue = "已保存，下次启动游戏生效。" } catch { message.stringValue = error.localizedDescription; message.textColor = .systemOrange } }
}

extension Client {
    static var nativeEdition: Bool {
        #if CLIENT_UI_PROBE
        return true
        #else
        return Bundle.main.infoDictionary?["TOTKNativeEdition"] as? Bool == true
        #endif
    }
    var nativeData: URL { FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("MacNativeGames/TOTK", isDirectory: true) }
    func nativeError(_ message: String) { let alert = NSAlert(); alert.messageText = "游戏"; alert.informativeText = message; alert.runModal() }
    func validGame(_ url: URL) -> Bool {
        guard let bundle = Bundle(url: url), bundle.bundleIdentifier == "org.macnativegames.totk", bundle.infoDictionary?["CFBundleShortVersionString"] as? String == "1.4.3", (bundle.infoDictionary?["TOTKInputConfigVersion"] as? Int ?? 0) >= 1 else { return false }
        return FileManager.default.isExecutableFile(atPath: url.appendingPathComponent("Contents/Resources/totk/build/totk-native").path)
    }
    @objc func chooseNativeGame() {
        let panel = NSOpenPanel(); panel.title = "选择原生游戏"; panel.message = "选择支持自定义键位的王国之泪 1.4.3 游戏 App。"; panel.allowedContentTypes = [.applicationBundle]; panel.canChooseDirectories = false
        guard panel.runModal() == .OK, let url = panel.url else { return }
        guard validGame(url) else { nativeError("请选择支持自定义键位的原生 1.4.3 游戏 App。此客户端不启动模拟器。"); return }
        settings.set(url.path, forKey: "nativeGamePath"); feedback.stringValue = "已选择：" + url.lastPathComponent
    }
    @objc func launchNativeGame() {
        if settings.string(forKey: "nativeGamePath").flatMap({ URL(fileURLWithPath: $0) }).map(validGame) != true { chooseNativeGame() }
        guard let path = settings.string(forKey: "nativeGamePath") else { return }; let url = URL(fileURLWithPath: path)
        guard validGame(url) else { return }
        // Always use the packaged launcher: it owns the production GameSlot and profile.
        let configuration = NSWorkspace.OpenConfiguration(); configuration.activates = true
        NSWorkspace.shared.openApplication(at: url, configuration: configuration) { [weak self] _, error in
            DispatchQueue.main.async { if let error = error { self?.nativeError(error.localizedDescription) } else { self?.feedback.stringValue = "已请求启动游戏，进入场景后自动连接。" } }
        }
    }
    @objc func editNativeKeys() {
        do {
            if bindingsWindow == nil {
                guard let schema = Bundle.main.url(forResource: "input-actions", withExtension: "json") else { throw InputConfigError(message: "缺少游戏键位定义。") }
                bindingsWindow = try KeyBindingsWindow(bindings: NativeBindings(directory: nativeData, schemaURL: schema))
            } else if bindingsWindow?.window?.isVisible != true { bindingsWindow = nil; editNativeKeys(); return }
            bindingsWindow?.showWindow(nil); bindingsWindow?.window?.makeKeyAndOrderFront(nil)
        } catch { nativeError(error.localizedDescription) }
    }
}

#if CLIENT_UI_PROBE
extension Client {
    func renderNativePreview() {
        let output = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
        func image(_ window: NSWindow, _ name: String) {
            let view = window.contentView!; view.layoutSubtreeIfNeeded()
            let bitmap = view.bitmapImageRepForCachingDisplay(in: view.bounds)!
            view.cacheDisplay(in: view.bounds, to: bitmap)
            try! bitmap.representation(using: .png, properties: [:])!.write(to: output.appendingPathComponent(name))
        }
        image(window, "client.png")
        let schema = URL(fileURLWithPath: CommandLine.arguments[2])
        let editor = try! KeyBindingsWindow(bindings: NativeBindings(directory: output.appendingPathComponent("preview-config"), schemaURL: schema))
        image(editor.window!, "keys.png")
        // Call the real responder directly; no OS input, user focus or game state is touched.
        let first = editor.buttons[0]; editor.record(first)
        let event = NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: [], timestamp: 0, windowNumber: 0, context: nil, characters: "x", charactersIgnoringModifiers: "x", isARepeat: false, keyCode: 7)!
        first.keyDown(with: event); precondition(editor.bindings.keys[0] == [7])
        editor.bindings.keys[0] = [2]; editor.refresh(); precondition(!editor.saveButton.isEnabled)
        image(editor.window!, "keys-conflict.png")
        editor.resetBindings(); precondition(editor.bindings.keys[0] == [38] && editor.saveButton.isEnabled)
        editor.devicePicker.selectedSegment = 1; editor.changeDevice()
        let menu = editor.mouseMenus[0]; menu.selectItem(at: 3); editor.mouseChanged(menu); precondition(editor.bindings.mouse[0] == "x")
        editor.resetBindings()
        if let root = editor.window?.contentView?.subviews.first as? NSStackView,
           let scroll = root.arrangedSubviews.compactMap({ $0 as? NSScrollView }).first, let document = scroll.documentView {
            document.scroll(NSPoint(x: 0, y: max(0, document.bounds.height - scroll.contentView.bounds.height)))
            image(editor.window!, "keys-mouse.png")
        }
        editor.devicePicker.selectedSegment = 2; editor.changeDevice()
        let controller = editor.controllerMenus[0]; controller.selectItem(at: 3); editor.controllerChanged(controller)
        precondition(editor.bindings.controller[0] == "x")
        image(editor.window!, "keys-controller.png")
        editor.resetBindings(); precondition(editor.bindings.controller == NativeBindings.controllerDefaults)
        print("PASS controller selection, device tabs and reset")
        print("PASS native UI layout, key capture, duplicate prevention, reset, mouse selection and scrolling")
    }
}
#endif
