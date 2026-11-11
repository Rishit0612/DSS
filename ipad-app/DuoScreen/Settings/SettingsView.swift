import SwiftUI

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss

    @AppStorage("serverHost") private var serverHost = "127.0.0.1"
    @AppStorage("serverPort") private var serverPort = "59000"
    @AppStorage("showFPS") private var showFPS = true
    @AppStorage("showLatency") private var showLatency = false

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Server Connection")) {
                    HStack {
                        Text("Host")
                        Spacer()
                        TextField("127.0.0.1", text: $serverHost)
                            .multilineTextAlignment(.trailing)
                            .keyboardType(.numbersAndPunctuation)
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                    }
                    HStack {
                        Text("Port")
                        Spacer()
                        TextField("59000", text: $serverPort)
                            .multilineTextAlignment(.trailing)
                            .keyboardType(.numberPad)
                    }
                }

                Section(header: Text("Display")) {
                    Toggle("Show FPS", isOn: $showFPS)
                    Toggle("Show Latency", isOn: $showLatency)
                }

                Section(header: Text("About")) {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("1.0.0 (Phase 1 MVP)")
                            .foregroundColor(.secondary)
                    }
                }

                Section(header: Text("Connection Info")) {
                    Text("""
                    DuoScreen connects to the Windows server over TCP. \
                    For USB connection, use iproxy to tunnel the port:

                    iproxy \(serverPort) \(serverPort)

                    Then connect to 127.0.0.1:\(serverPort).

                    For Wi-Fi, enter the server machine's IP address \
                    as the host above.
                    """)
                    .font(.caption)
                    .foregroundColor(.secondary)
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
}
