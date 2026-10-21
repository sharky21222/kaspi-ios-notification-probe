# Accessory Capability Findings, 2026-10-21

## Real-Device Result

The patched Windows signer authenticated successfully and obtained a new signing
identity after the operator manually revoked the certificate used only by the
basic installation probe. It registered the isolated probe's App IDs and obtained
profiles. Its profile verification then stopped signing because the data-provider
profile did not authorize `com.apple.developer.accessory-data-provider = true`.

The Access Probe was NOT installed. No bank notification reception or background
transport was verified. Do not revoke the new certificate or repeat the same
login/install attempt to address this missing capability.

## Apple Xcode Evidence

Read public definitions from Xcode 27.0, build 27A266a, without an Apple account,
account signing keys, or provisioning profiles in CI. The relevant source is:

`Contents/SharedFrameworks/DVTPortal.framework/Versions/A/Resources/DVTPortalCachedPortalCapabilities.json`

All three records have `enabledByDefault: false`, `isRequiredInPlist: true` for
their entitlement, and list only these `validTeamTypes`:

- `APPLE_DEVELOPER_PROGRAM`
- `APPLE_DEVELOPER_ENTERPRISE_PROGRAM`

The capabilities are `ACCESSORY_DATA_PROVIDER`, `ACCESSORY_TRANSPORT_EXTENSION`,
and `ACCESSORY_TRANSPORT_SECURITY`. Free Personal Team is not included in this
Xcode snapshot. Its supported free provisioning path cannot grant these rights.
This is dated evidence of Apple's supported eligibility, not a claim about every
future Xcode release or a guarantee that paid membership makes our prototype work.

An abbreviated factual snapshot is in
`Tests/fixtures/xcode27-accessory-capabilities.json`. The full public audit was
performed by Codemagic build
https://codemagic.io/app/6ad7d4e1be3174cbbf17ec23/build/6ad85c8c454d2506f7abb4ff
from source commit `284228c8510f90eb06449c00d8fab383d09a9cbc`.

The audit workflow reads only Xcode's installed public resources. It has no
account-access step and can be rerun when Apple's eligibility rules change.

## Signer Limitation and Next Boundary

Version 0.1.0 discovers and recursively signs ExtensionKit bundles, but does not
enable accessory capabilities in the developer portal. Therefore the original
missing-profile error alone was not proof of universal Personal Team ineligibility.
The separate Xcode eligibility audit supplies the supported-team evidence above.

Keep profile verification enabled. Adding an unauthorized Boolean to a signature
does not replace an Apple-authorized provisioning profile. Do not strip extensions
or claim that installing the basic probe enables notification access.

No paid subscription is recommended as a verified solution. The encrypted
accessory transport remains unimplemented in this capability probe. A free
Windows notification investigation can continue with ANCS / Phone Link, whose
reliability for the user's bank notification content must still be tested.

## Apple Documentation

- https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.accessory-data-provider
- https://developer.apple.com/documentation/technotes/tn3125-inside-code-signing-provisioning-profiles
- https://developer.apple.com/documentation/accessorynotifications
