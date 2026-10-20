# Kaspi iPhone Probe

Isolated, zero-subscription-cost experiment for iOS 26.5 or later. This repository
contains no KaspiDonate source, payment details, credentials, phone database,
donation history, or Apple account data.

Status: both arm64 iPhone packages compiled with Xcode 27.0 on 2026-10-21
(source commit `bcf6d2b`). All three capability extensions are included. The
basic app launched in the simulator; bundle-ID preflight, Swift signature-parser
checks, and eight Python tests passed. Downloaded IPA hashes, ZIP integrity,
executables, and bundle metadata were verified. The Windows synthetic receiver
and a short BLE advertising/cleanup check have also passed. Free-account signing,
installation, entitlements, and notification reception on a real iPhone were
initially unverified. See the real-device results below. Do not treat this as a
validated bank notification bridge.

## Real-device results (2026-10-21)

- The basic Install Probe was installed using a free Apple account and opened
  on iOS 27.0.1. Its authenticated synthetic LAN request reached the Windows
  receiver and returned successfully. The temporary receiver was then stopped.
- Access Probe installation through Sideloadly 0.71.1 failed because iOS reported
  that `ProbeTransport.appex` lacked the Boolean entitlement
  `com.apple.developer.accessory-transport-extension` after re-signing.
- A binary-signature audit of the original downloaded IPA and Sideloadly's
  cached source IPA confirmed that each of the three extensions originally had
  its correct entitlement set to Boolean `true`. Both source IPA hashes matched
  the build manifest. The post-sign package/profile has not been obtained, so
  this does not establish whether Apple's profile supports these capabilities.
- Sideloadly's official changelog restricts its custom-entitlements feature to
  Apple Developer Program accounts and Patreon subscribers. No paid option was
  enabled, extensions were not removed, and no signing restrictions were bypassed.
- Notification access and bank notification reception remain UNVERIFIED. An
  unchanged Retry is not a successful test. Do not describe either IPA as a
  working bank notification bridge or assume payment would resolve the issue.

Signing-tool reference: <https://sideloadly.io/changelog>

**This is not a working bank notification bridge.** The first gate is whether
the phone accepts a free re-sign and retains the required extension entitlements.
A successful installation or permission prompt does NOT prove notification
receipt, background reliability, encrypted transport, or compatibility with
production donation alerts.

## Packages

- `Kaspi-Install-Probe.ipa`: basic install and synthetic local-network test.
- `Kaspi-Access-Probe.ipa`: the same app with all three required accessory
  extensions and their requested entitlement keys.

Packages are ad-hoc signed only to preserve the requested entitlement metadata
for the installer. They contain **no Apple certificate or provisioning profile**
and require re-signing with the user's own Apple account. The access probe may
fail signing or installation if the account cannot obtain these capabilities.
Do not strip extensions to turn such a failure into an apparent success.

The security and transport handlers deliberately report transport unavailable.
No fake key exchange, plaintext bank forwarding, or false success is provided.
The notification handler never reads notification content or changes donations.

## Free installation on Windows

1. Download Sideloadly only from <https://sideloadly.io/>.
2. Connect the unlocked iPhone by USB. Complete device trust and Developer Mode
   prompts yourself, if needed. Never send account passwords or 2FA codes in chat.
3. Install the **Install Probe first**, using your own free Apple account.
4. If it launches, try the **Access Probe** without removing its extensions.
5. Keep the exact signing/installation error if it fails. If it launches, use
   `Отчёт проверки` to share the diagnostic report. Reports exclude pairing keys,
   IP addresses, account credentials, bank messages and donor names.

Free personal provisioning normally expires after seven days and has device,
App ID, and installed-app limits. Automatic refresh is an installer feature;
it does not grant additional iOS entitlements.

Do not uninstall existing Apple drivers or modify Phone Link just for this test.
If the installer requests driver changes, stop and check the requirement first.

## Windows connectivity and accessory test

No installed service, autostart, firewall change, or production API is created.
The receiver accepts only authenticated synthetic pings for up to 15 minutes.
It never accepts bank text or donation events. It binds port 5127 on the chosen
private network interface, not the KaspiDonate server port.

```powershell
python windows/receiver.py --host YOUR_PRIVATE_PC_IPV4
```

Enter the displayed IPv4 address and temporary key into the phone app. A phone
response means only that this synthetic network request worked. Keep the key
private; it expires when the receiver closes.

For the system accessory picker, optionally publish a separate read-only BLE
service, using Python 3.12+ with the dependencies in `windows/requirements.txt`:

```powershell
python windows/receiver.py --host YOUR_PRIVATE_PC_IPV4 --advertise
```

This does not pair the phone, authorize notifications, enable Bluetooth, reset
the adapter, or stop another application's connection. Complete any operating
system consent yourself. Stop with Ctrl+C; no startup entry remains.

## Build and test

The manual GitHub Actions workflow uses only a **standard public-repository
macOS runner**, which GitHub documents as free. It never uses paid/larger
runners, Apple account secrets, private-repository minutes, or artifact storage.
Outputs are attached to a GitHub pre-release.

If GitHub Actions is unavailable, `codemagic.yaml` supports a **personal Free**
Codemagic account using the included macOS M2 minutes. Builds are manual, capped
at 20 minutes, and require no Apple signing assets. Do not enable billing,
choose a paid/team plan, use an M4 instance, or start without sufficient free
M2 minutes remaining. Grant repository access only to this isolated project.
Codemagic stores the generated test artifacts within its included plan storage.

On Codemagic, add this repository as a native iOS app, select `codemagic.yaml`
from branch `main`, then run workflow `probe-ios`. It is a build-for-re-signing
workflow, not App Store/TestFlight distribution.

```sh
xcodegen generate
xcodebuild -project KaspiProbe.xcodeproj -scheme InstallProbe -sdk iphoneos CODE_SIGNING_ALLOWED=NO build
python3 -m unittest discover -s Tests -p 'test_*.py' -v
```

## Official References

- Apple Accessory Notifications: <https://developer.apple.com/documentation/accessorynotifications>
- Required extensions: <https://developer.apple.com/documentation/accessorytransportextension/receiving-ios-notifications-on-an-accessory>
- Local-network transport: <https://developer.apple.com/documentation/accessorytransportextension/accessorytransport/localnetwork>
- Free personal provisioning: <https://developer.apple.com/help/account/basics/about-your-developer-account>
- GitHub public runner pricing: <https://docs.github.com/en/actions/reference/runners/github-hosted-runners>
- Sideloadly FAQ: <https://sideloadly.io/faq>

Developer testing outside the EU and customer availability are different:
Apple permits development/testing in any region, but restricts customer use
of the framework to eligible EU devices/accounts. No regional bypass is provided.
