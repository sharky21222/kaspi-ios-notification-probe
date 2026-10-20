import SwiftUI

struct ProbeView: View {
    @StateObject private var model = ProbeModel()
    @State private var host = ""
    @State private var token = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Label(model.basic ? "Проверка установки" : "Проверка разрешений", systemImage: "iphone.gen3.radiowaves.left.and.right")
                        .font(.headline)
                    LabeledContent("Версия", value: "0.1.0")
                    LabeledContent("Приём донатов", value: "Не подключён")
                }
                if !model.basic {
                    Section("Расширения и подпись") {
                        ForEach(model.checks) { check in
                            HStack(alignment: .top, spacing: 12) {
                                Image(systemName: check.entitlement == true ? "checkmark.shield" : "exclamationmark.shield")
                                    .foregroundStyle(check.entitlement == true ? Color.mint : Color.yellow)
                                    .frame(width: 24)
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(check.name).font(.subheadline.weight(.semibold))
                                    Text(!check.present ? "Расширение отсутствует" : check.entitlement == true ? "Ключ есть в подписи" : check.entitlement == false ? "Ключ удалён из подписи" : "Подпись не определена")
                                        .font(.caption).foregroundStyle(.secondary)
                                }
                            }.padding(.vertical, 4)
                        }
                        Button("Обновить проверку", systemImage: "arrow.clockwise") { model.audit() }
                    }
                    Section("Разрешение iOS") {
                        LabeledContent("Получатель", value: model.accessorySelected ? "Выбран" : "Не выбран")
                        Button("Найти ПК", systemImage: "antenna.radiowaves.left.and.right") {
                            Task { await model.chooseAccessory() }
                        }.disabled(!model.accessoryReady || model.busy)
                        Button("Запросить пересылку", systemImage: "bell.badge") {
                            Task { await model.requestForwarding() }
                        }.disabled(!model.accessorySelected || model.busy)
                        LabeledContent("Статус", value: model.forwarding)
                    }
                }
                Section("Соединение с Windows") {
                    TextField("IPv4-адрес ПК", text: $host).keyboardType(.decimalPad)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                    SecureField("Ключ проверки", text: $token)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                    Button("Проверить соединение", systemImage: "network") {
                        Task { await model.testNetwork(host: host, token: token) }
                    }.disabled(model.busy || host.isEmpty || token.isEmpty)
                    LabeledContent("Статус", value: model.connection)
                }
                if !model.error.isEmpty {
                    Section("Результат") { Text(model.error).foregroundStyle(.orange).textSelection(.enabled) }
                }
                Section {
                    ShareLink(item: model.report) { Label("Отчёт проверки", systemImage: "square.and.arrow.up") }
                }
            }
            .navigationTitle("Kaspi Probe")
            .toolbar { if model.busy { ProgressView() } }
        }
    }
}
