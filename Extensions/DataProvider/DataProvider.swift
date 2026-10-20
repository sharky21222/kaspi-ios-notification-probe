import AccessoryNotifications
import AccessoryTransportExtension
import ExtensionFoundation
import OSLog

@main
struct ProbeDataProvider: AccessoryDataProvider {
    var extensionPoint: AppExtensionPoint {
        Identifier("com.apple.accessory-data-provider")
        Implementing { NotificationsForwarding { NotificationProbeHandler() } }
    }
}

final class NotificationProbeHandler: NotificationsForwarding.AccessoryNotificationsHandler, @unchecked Sendable {
    private let logger = Logger(subsystem: "site.shrks.kaspiprobe", category: "capability")
    func didActivate(for session: NotificationsForwarding.Session) { logger.notice("notification_extension_activated") }
    func didInvalidate() {}
    func addNotification(_ notification: AccessoryNotification, alertingContext: AlertingContext) async throws -> Bool {
        // Capability test only: never inspect, store, forward, or alert for bank content.
        logger.notice("notification_callback_received_content_not_read")
        return false
    }
    func updateNotification(_ notification: AccessoryNotification) {}
    func removeNotification(identifier: AccessoryNotification.Identifier) {}
    func removeAllNotifications() {}
    func messageHandler(_ message: TransportMessage) {}
}
