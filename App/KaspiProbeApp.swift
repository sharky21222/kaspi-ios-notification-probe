import SwiftUI

@main
struct KaspiProbeApp: App {
    var body: some Scene {
        WindowGroup { ProbeView().tint(.cyan).preferredColorScheme(.dark) }
    }
}
