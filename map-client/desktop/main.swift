import AppKit

let application = NSApplication.shared
let client = Client()
application.delegate = client
application.setActivationPolicy(.regular)
application.run()
