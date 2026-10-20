import AccessoryTransportExtension
import ExtensionFoundation

@main
struct ProbeSecurity: AccessoryTransportSecurity {
    @AppExtensionPoint.Bind
    static var boundExtensionPoint: AppExtensionPoint { Identifier("com.apple.accessory-transport-security") }

    func accept(sessionRequest: AccessorySecuritySession.Request) -> AccessorySecuritySession.Request.Decision {
        sessionRequest.accept { SecurityProbeHandler() }
    }
}

final class SecurityProbeHandler: AccessorySecuritySession.EventHandler {
    func messageReceived(_ message: SecurityMessage, completion: @escaping @Sendable (AccessoryMessage.Result) -> Void) {
        // No fake key exchange: a capability check must not claim a working transport.
        completion(.failure(.transportUnavailable))
    }
    func sessionInvalidated(error: (any Error)?) {}
}
