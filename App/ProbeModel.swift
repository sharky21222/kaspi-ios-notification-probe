import AccessoryNotifications
import AccessorySetupKit
import CoreBluetooth
import Foundation
import UIKit

struct ExtensionCheck: Identifiable {
    var id: String { name }
    let name: String
    let present: Bool
    let entitlement: Bool?
}

@MainActor
final class ProbeModel: ObservableObject {
    @Published var checks: [ExtensionCheck] = []
    @Published var accessoryReady = false
    @Published var accessorySelected = false
    @Published var forwarding = "Не проверено"
    @Published var connection = "Нет проверки"
    @Published var error = ""
    @Published var busy = false
    private let accessorySession = ASAccessorySession()
    private var accessory: ASAccessory?
    let basic = Bundle.main.object(forInfoDictionaryKey: "ProbeVariant") as? String == "basic"

    init() {
        audit()
        accessorySession.activate(on: .main) { [weak self] event in
            Task { @MainActor in
                guard let self else { return }
                if event.eventType == .activated {
                    self.accessoryReady = true
                    self.accessory = self.accessorySession.accessories.first
                }
                if event.eventType == .accessoryAdded { self.accessory = event.accessory }
                self.accessorySelected = self.accessory != nil
            }
        }
    }

    func audit() {
        let names = [
            ("ProbeDataProvider", "com.apple.developer.accessory-data-provider"),
            ("ProbeSecurity", "com.apple.developer.accessory-transport-security"),
            ("ProbeTransport", "com.apple.developer.accessory-transport-extension")
        ]
        checks = names.map { name, key in
            let candidates = ["Extensions", "PlugIns"].map {
                Bundle.main.bundleURL.appendingPathComponent($0).appendingPathComponent(name + ".appex")
            }
            guard let directory = candidates.first(where: { FileManager.default.fileExists(atPath: $0.path) }),
                  let bundle = Bundle(url: directory), let executable = bundle.executableURL else {
                return ExtensionCheck(name: name, present: false, entitlement: nil)
            }
            let values = try? SignatureAudit.entitlements(in: Data(contentsOf: executable))
            let allowed = values.map { $0[key] as? Bool == true }
            return ExtensionCheck(name: name, present: true, entitlement: allowed)
        }
    }

    func chooseAccessory() async {
        error = ""
        let descriptor = ASDiscoveryDescriptor()
        descriptor.bluetoothServiceUUID = CBUUID(string: "5CC0C4AB-2D7F-4B59-B527-0D867E11FD10")
        let item = ASPickerDisplayItem(name: "Kaspi Probe PC",
                                      productImage: UIImage(systemName: "desktopcomputer")!, descriptor: descriptor)
        do { try await accessorySession.showPicker(for: [item]) }
        catch { self.error = error.localizedDescription }
    }

    func requestForwarding() async {
        guard !basic, let accessory else { return }
        error = ""
        busy = true
        defer { busy = false }
        do {
            let decision = try await AccessoryNotificationCenter().requestForwarding(for: accessory)
            // Authorization is separate from successful receipt and transport.
            forwarding = String(describing: decision)
        } catch {
            forwarding = "Не разрешено"
            self.error = error.localizedDescription
        }
    }

    func testNetwork(host: String, token: String) async {
        error = ""
        let ip = host.trimmingCharacters(in: .whitespacesAndNewlines)
        let parts = ip.split(separator: ".").compactMap { Int($0) }
        guard parts.count == 4, parts.allSatisfy({ (0...255).contains($0) }),
              parts[0] == 10 || (parts[0] == 192 && parts[1] == 168) ||
              (parts[0] == 172 && (16...31).contains(parts[1])),
              let url = URL(string: "http://\(ip):5127/probe"), token.count == 64,
              token.allSatisfy({ $0.isHexDigit }) else {
            error = "Нужны локальный IPv4-адрес ПК и 64-значный ключ"
            return
        }
        busy = true
        defer { busy = false }
        do {
            var request = URLRequest(url: url, timeoutInterval: 8)
            request.httpMethod = "POST"
            request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: ["kind": "connectivity-test", "nonce": UUID().uuidString])
            let configuration = URLSessionConfiguration.ephemeral
            configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
            let session = URLSession(configuration: configuration)
            defer { session.invalidateAndCancel() }
            let (data, response) = try await session.data(for: request)
            guard (response as? HTTPURLResponse)?.statusCode == 200,
                  let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                  json["ok"] as? Bool == true else {
                connection = "Нет подтверждения"
                return
            }
            connection = "ПК ответил"
        } catch {
            connection = "Соединение не установлено"
            self.error = error.localizedDescription
        }
    }

    var report: String {
        let value: [String: Any] = [
            "version": "0.1.0", "variant": basic ? "basic" : "capabilities",
            "ios": UIDevice.current.systemVersion,
            "signatureChecks": checks.map { ["name": $0.name, "present": $0.present,
                "entitlementInSignature": $0.entitlement.map { $0 ? "yes" : "no" } ?? "unknown"] as [String: Any] },
            "accessorySelected": accessorySelected, "forwardingAuthorization": forwarding,
            "network": connection, "bankReceptionVerified": false
        ]
        let data = try? JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys])
        return data.flatMap { String(data: $0, encoding: .utf8) } ?? "{}"
    }
}
