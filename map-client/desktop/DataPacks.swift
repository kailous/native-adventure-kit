import AppKit
import UniformTypeIdentifiers

extension Client {
    @objc func importDataPacks() {
        let panel = NSOpenPanel()
        panel.title = "导入地图或攻略数据包"
        panel.message = "选择 .totkpack 文件。校验后保存到客户端数据目录，旧版本会保留。"
        panel.allowedContentTypes = [UTType(filenameExtension: "totkpack") ?? .data]
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        guard panel.runModal() == .OK else { return }
        installDataPacks(panel.urls)
    }

    @objc func showDataPackInfo() {
        guard let info = connection, let base = info["url"] as? String, let url = URL(string: base + "api/data-packs") else {
            let alert = NSAlert(); alert.messageText = "请先启动服务"; alert.runModal(); return
        }
        URLSession.shared.dataTask(with: url) { data, _, error in
            let packs = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: [String: Any]] }
            DispatchQueue.main.async {
                let alert = NSAlert(); alert.messageText = "已安装数据包"
                if let packs = packs {
                    alert.informativeText = [("map", "地图与地形"), ("guide", "攻略与图鉴")].map { key, title in
                        guard let pack = packs[key], pack["installed"] as? Bool == true else { return title + "：未安装或不可用" }
                        let version = pack["version"] as? String ?? "—"
                        let size = (pack["bytes"] as? NSNumber)?.doubleValue ?? 0
                        let terrain = key == "map" ? "\n地形覆盖不完整，部分坐标尚未验证。" : ""
                        return title + "：" + version + String(format: " · %.1f MiB", size / 1048576) + terrain
                    }.joined(separator: "\n\n")
                } else { alert.informativeText = error?.localizedDescription ?? "无法读取数据包信息" }
                alert.runModal()
            }
        }.resume()
    }

    @objc func showDataPacks() {
        let base = Self.nativeEdition ? support.deletingLastPathComponent().appendingPathComponent("TOTK Offline") : support
        let folder = base.appendingPathComponent("DataPacks", isDirectory: true)
        do {
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            NSWorkspace.shared.open(folder)
        } catch {
            let alert = NSAlert(); alert.messageText = "无法打开数据包目录"; alert.informativeText = error.localizedDescription; alert.runModal()
        }
    }

    func application(_ sender: NSApplication, openFiles filenames: [String]) {
        #if !CLIENT_UI_PROBE
        let urls = filenames.map { URL(fileURLWithPath: $0) }
        if window == nil { pendingDataPacks += urls } else { installDataPacks(urls) }
        #endif
        sender.reply(toOpenOrPrint: .success)
    }

    func installDataPacks(_ urls: [URL]) {
        guard !importingDataPacks, !urls.isEmpty else { return }
        importingDataPacks = true
        feedback.stringValue = "正在校验并导入数据包，完成后自动重启服务…"
        let supportPath = support.path
        let contentPath = (Self.nativeEdition ? support.deletingLastPathComponent().appendingPathComponent("TOTK Offline") : support).path
        let executable = Bundle.main.resourceURL!.appendingPathComponent("backend/totk-service")
        DispatchQueue.global(qos: .userInitiated).async {
            var failure: String?
            for url in urls {
                do {
                    let child = Process(); child.executableURL = executable
                    child.arguments = ["--import-pack", url.path]
                    var environment = ProcessInfo.processInfo.environment
                    environment["TOTK_SUPPORT_ROOT"] = supportPath
                    environment["TOTK_DATA_SUPPORT_ROOT"] = contentPath
                    child.environment = environment
                    let pipe = Pipe(); child.standardOutput = pipe; child.standardError = pipe
                    try child.run()
                    let output = pipe.fileHandleForReading.readDataToEndOfFile()
                    child.waitUntilExit()
                    if child.terminationStatus != 0 {
                        failure = String(data: output, encoding: .utf8) ?? "数据包导入失败"
                        break
                    }
                } catch { failure = error.localizedDescription; break }
            }
            DispatchQueue.main.async {
                self.importingDataPacks = false
                // Reload even when a later file fails: earlier files may have installed successfully.
                self.startBackend()
                let alert = NSAlert()
                alert.messageText = failure == nil ? "数据包导入完成" : "数据包导入未全部完成"
                alert.informativeText = failure ?? "数据包已校验并启用。服务正在重新启动，旧版本保留在数据包目录中。"
                alert.runModal()
            }
        }
    }
}
