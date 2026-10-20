import AccessoryTransportExtension
import ExtensionFoundation

@main
struct ProbeTransport: AccessoryTransportAppExtension {
    @AppExtensionPoint.Bind
    static var boundExtensionPoint: AppExtensionPoint { Identifier("com.apple.accessory-transport-extension") }

    func accept(sessionRequest: AccessoryTransportSession.Request) -> AccessoryTransportSession.Request.Decision {
        sessionRequest.accept { TransportProbeHandler() }
    }
}

final class TransportProbeHandler: AccessoryTransportSession.EventHandler {
    func messageReceived(_ message: TransportMessage, completion: @escaping @Sendable (AccessoryMessage.Result) -> Void) {
        completion(.failure(.transportUnavailable))
    }
    func dataEventHandler(event: AccessoryTransportSession.DataEvent) {}
    func invalidationHandler(error: AccessoryTransportSession.Error?) {}
    func sessionInvalidated(error: AccessoryTransportSession.Error?) {}
}
