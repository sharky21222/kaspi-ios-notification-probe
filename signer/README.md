# Kaspi Probe Signer (experimental)

This is a separate, narrowly scoped Windows console tool, NOT an iLoader release.
It supports only the isolated Kaspi Access Probe. It is not integrated with
KaspiDonate. Successful signing or installation does not prove that iOS grants
notification access, nor that bank notifications or background delivery work.

## Commands (Windows PowerShell)

```powershell
.\kaspi-probe-signer.exe inspect "$HOME\Downloads\Kaspi-Access-Probe.ipa"
.\kaspi-probe-signer.exe check-account
.\kaspi-probe-signer.exe install-probe "$HOME\Downloads\Kaspi-Access-Probe.ipa"
```

- `inspect` is offline. It validates all three ExtensionKit bundles without
  modifying the original IPA. Direct application directories are rejected.
- `check-account` logs in and reads the team, certificate count and available
  App ID count. It does not create/revoke certificates or register/install apps.
- `install-probe` accepts only source IPA SHA-256
  `3a0598d681a89a8c8c7f59b5af9732581e38becf017571660381884d4ffc37bf`.
  It requires typing `INSTALL TEST PROBE` locally before any Apple account
  changes. It may create one new certificate, register four App IDs and the
  connected device, create profiles and install the test app. Existing
  certificates are NEVER revoked. If certificate slots are full it stops.
  If any profile lacks the Boolean accessory entitlement, it stops before
  signing; it does not remove extensions, fabricate permissions or bypass iOS.
  App ID / certificate changes already made are not automatically rolled back.

Keep exactly one unlocked iPhone connected by USB, with the existing Apple device
drivers. Approve trust or developer-mode prompts yourself. No administrator
rights, OS security changes, paid services or cloud Apple credentials are needed
by this tool. Capability eligibility for a free Personal Team is unconfirmed.

Apple ID password and 2FA code are entered only in the local hidden console
prompts, never as command-line arguments, in chat, in CI, or in build variables.
The tool does not save your Apple password/session. Technical Anisette state
and any newly created signing certificate/private key use Windows Credential
Manager under the separate `kaspi-probe-signer` service. It does not read
iLoader's saved account. Anisette uses `https://mac-ani.jkcoxson.com`; the
authentication library sends Apple authentication requests to Apple. TLS
validation stays enabled. Account commands refuse CI or redirected consoles.

## Rebuild / Replace the LGPL Library

The accompanying `source.zip` contains the complete tool source, modified
library sources, lockfile, public CA certificates and build instructions.
Extract it and edit `signer/vendor/apple-codesign-quick` as desired. No binary
patching or reverse engineering is required to replace/relink that library.

On Windows with Rust 1.99.1 and the normal MSVC build tools:

```powershell
cd signer
cargo test --locked -p kaspi-probe-signer
cargo test --locked -p apple-codesign-quick --lib
cargo build --locked --release --bin kaspi-probe-signer
```

On an Apple Silicon Mac, `bash scripts/build_signer.sh test` followed by
`bash scripts/build_signer.sh windows` reproduces the CI build using cargo-xwin,
LLVM and Microsoft's Windows SDK. All are build dependencies; Apple ID and
signing keys are never needed to compile or run the offline tests.

See `THIRD_PARTY.md` and the bundled licenses. This build is experimental and
has no commercial code-signing certificate for the Windows executable.
