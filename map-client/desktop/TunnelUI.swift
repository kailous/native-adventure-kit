import AppKit
import Security

/// Account credentials are stored in Keychain, never UserDefaults, logs, or exported MCP JSON.
enum TunnelCredential {
    static let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: "local.totk.offline.ngrok", kSecAttrAccount as String: "authtoken"]
    static func load() -> String? {
        var q = query; q[kSecReturnData as String] = true; q[kSecMatchLimit as String] = kSecMatchLimitOne
        var value: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &value) == errSecSuccess, let data = value as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
    static func save(_ value: String) throws {
        let attrs: [String: Any] = [kSecValueData as String: Data(value.utf8)]
        var status = SecItemUpdate(query as CFDictionary, attrs as CFDictionary)
        if status == errSecItemNotFound { var q = query; q.merge(attrs) { _, new in new }; status = SecItemAdd(q as CFDictionary, nil) }
        guard status == errSecSuccess else { throw NSError(domain: NSOSStatusErrorDomain, code: Int(status), userInfo: [NSLocalizedDescriptionKey: "无法将 ngrok 令牌保存到钥匙串（\(status)）"]) }
    }
}

extension Client {
    @objc func showTunnelSettings() {
        guard connection != nil else { feedback.stringValue = "请先启动服务"; return }
        let alert = NSAlert(); alert.messageText = "固定地址 MCP 隧道"
        alert.informativeText = "使用 ngrok 账号分配的固定域名，无需购买域名。开启后，有 MCP 密钥的远程客户端可读取游戏数据，并控制林克移动、攻击等动作；地图网页和存档下载不会开放。"
        alert.addButton(withTitle: "保存并开启"); alert.addButton(withTitle: "关闭"); alert.addButton(withTitle: "停止隧道")
        let domain = NSTextField(string: settings.string(forKey: "tunnelDomain") ?? ""); domain.placeholderString = "example.ngrok-free.app"; domain.font = .monospacedSystemFont(ofSize: 13, weight: .regular)
        let token = NSSecureTextField(string: ""); token.placeholderString = "填写 ngrok Authtoken；已保存时留空保持"
        let automatic = NSButton(checkboxWithTitle: "下次启动客户端时自动开启隧道", target: nil, action: nil); automatic.state = settings.bool(forKey: "tunnelAutoStart") ? .on : .off
        let state = label(tunnelDescription(), 12, ConsoleTheme.muted)
        let links = row([button("获取固定域名与令牌", #selector(openTunnelAccount)), button("复制远程 MCP 配置", #selector(copyRemoteMCP))])
        let content = column([label("固定域名", 12), domain, label("账号令牌（保存到 macOS 钥匙串）", 12), token, automatic, state, links], spacing: 10)
        content.frame = NSRect(x: 0, y: 0, width: 540, height: 250)
        domain.widthAnchor.constraint(equalToConstant: 540).isActive = true; token.widthAnchor.constraint(equalTo: domain.widthAnchor).isActive = true
        alert.accessoryView = content
        let result = alert.runModal()
        if result == .alertThirdButtonReturn { settings.set(false, forKey: "tunnelAutoStart"); tunnelRequest(["action": "stop"]); return }
        guard result == .alertFirstButtonReturn else { return }
        let value = domain.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        let publicURL = value.contains("://") ? value : "https://" + value
        guard let url = URL(string: publicURL), url.scheme == "https", let host = url.host, url.user == nil, url.password == nil, url.port == nil, ["", "/", "/mcp"].contains(url.path), url.query == nil, url.fragment == nil,
              host.range(of: "^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.(?:ngrok-free\\.(?:app|dev)|ngrok\\.(?:app|dev|io))$", options: .regularExpression) != nil else {
            let error = NSAlert(); error.messageText = "请输入 ngrok 分配的固定域名"; error.runModal(); return
        }
        let entered = token.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let credential = entered.isEmpty ? TunnelCredential.load() : entered, !credential.isEmpty else {
            let error = NSAlert(); error.messageText = "请填写 ngrok Authtoken"; error.runModal(); return
        }
        do {
            if !entered.isEmpty { try TunnelCredential.save(entered) }
            settings.set(host, forKey: "tunnelDomain"); settings.set(automatic.state == .on, forKey: "tunnelAutoStart")
            tunnelRequest(["action": "start", "domain": host, "authtoken": credential])
        } catch { NSAlert(error: error).runModal() }
    }
    @objc func openTunnelAccount() { NSWorkspace.shared.open(URL(string: "https://dashboard.ngrok.com/get-started/your-authtoken")!) }
    func tunnelDescription() -> String {
        switch tunnelInfo["state"] as? String {
        case "connected": return "固定隧道已连接 · " + (tunnelInfo["url"] as? String ?? "")
        case "starting": return (tunnelInfo["error"] as? String) ?? "正在连接固定隧道…"
        case "error": return tunnelInfo["error"] as? String ?? "隧道连接失败"
        default: return "隧道未开启 · 本地 MCP 可正常使用"
        }
    }
    func tunnelRequest(_ message: [String: Any]? = nil) {
        if tunnelRequestRunning { if let message = message { pendingTunnelRequest = message }; return }
        guard let child = backend, let base = connection?["url"] as? String, let url = URL(string: base + "api/mcp-tunnel"), let token = connection?["token"] as? String else { return }
        tunnelRequestRunning = true
        var request = URLRequest(url: url); request.timeoutInterval = 15; request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        if let message = message { request.httpMethod = "POST"; request.httpBody = try? JSONSerialization.data(withJSONObject: message); request.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            DispatchQueue.main.async {
                guard let self = self, self.backend === child else { return }; self.tunnelRequestRunning = false
                if let data = data, let info = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    if (response as? HTTPURLResponse)?.statusCode == 200 { self.tunnelInfo = info }
                    else { self.tunnelInfo = ["state": "error", "error": info["error"] as? String ?? "隧道操作失败"] }
                } else if message != nil { self.tunnelInfo = ["state": "error", "error": "隧道请求失败，请重试"] }
                let state = self.tunnelInfo["state"] as? String
                if state == "connected" { self.mcpState.stringValue = "固定隧道\n已连接"; self.mcpDot.textColor = ConsoleTheme.mint }
                else if state == "starting" { self.mcpState.stringValue = "本地已就绪\n隧道连接中"; self.mcpDot.textColor = ConsoleTheme.gold }
                else if state == "error" { self.mcpState.stringValue = "本地已就绪\n隧道连接失败"; self.mcpDot.textColor = ConsoleTheme.gold }
                else { self.mcpState.stringValue = "本地 HTTP\n服务已就绪"; self.mcpDot.textColor = ConsoleTheme.mint }
                self.mcpState.toolTip = self.tunnelDescription()
                self.recordEvent("tunnel", self.tunnelDescription())
                if message != nil { self.feedback.stringValue = self.tunnelDescription() }
                if let pending = self.pendingTunnelRequest { self.pendingTunnelRequest = nil; self.tunnelRequest(pending) }
            }
        }.resume()
    }
    func restoreTunnel() {
        if settings.bool(forKey: "tunnelAutoStart"), let domain = settings.string(forKey: "tunnelDomain"), let token = TunnelCredential.load() {
            tunnelRequest(["action": "start", "domain": domain, "authtoken": token])
        }
    }
    @objc func copyRemoteMCP() {
        guard let text = mcpConfig(remote: true) else { feedback.stringValue = "请先开启固定隧道，连接成功后再复制远程配置"; return }
        NSPasteboard.general.clearContents(); NSPasteboard.general.setString(text, forType: .string); feedback.stringValue = "远程 MCP 配置已复制 · 固定地址"
    }
}
