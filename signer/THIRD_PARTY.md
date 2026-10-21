# Third-Party Sources and Local Changes

The console tool is MIT licensed. Its libraries retain their original licenses.

## isideload 0.4.6 (MIT)

Source: https://crates.io/crates/isideload/0.4.6
Repository: https://github.com/nab138/isideload
Crate source revision: `8ca39b6203263e539408986e546c42e7c1cc3699`.
This is the version used by official iLoader 2.3.10, not newer development code.

Local modifications, 2026-10-21:
- Discover `Extensions/*.appex` as well as `PlugIns/*.appex`; preserve locations.
- Reject malformed extension bundles instead of silently dropping them.
- Give each temporary application extraction a new random name.
- Check each accessory extension's separate Apple-issued profile for its
  required Boolean entitlement before signing anything.

## apple-codesign-quick 0.1.0 (LGPL-2.1-or-later)

Source: https://crates.io/crates/apple-codesign-quick/0.1.0
Repository: https://github.com/Dadoum/apple-crates
Source revision: `91fad87099663252dec23e4b5332a8ca979986f4`.
Original crate SHA-256:
`519defc726db80b8a43836bbd6f69eb606a42783db799716a103436042593f0b`.

Local modifications, 2026-10-21:
- Discover and recursively sign nested `Extensions` bundles.
- Treat ExtensionKit binaries as nested code when sealing resources.
- Add a regression test for ExtensionKit discovery and resource handling.

The full LGPL text and modified library source are included. The complete
MIT-licensed application source and lockfile are supplied for rebuilding and
relinking with modified versions of this library. You may modify the application
for your own use and reverse engineer it for debugging those modifications.
No warranty is provided. See the license texts for full terms.

## Other Dependencies

`Cargo.lock` lists the exact crates.io dependencies and their checksums.
Their licenses remain applicable; Cargo downloads their source on rebuild.
The checked-in `.cer` files are public Apple CA certificates shipped in the
upstream libraries, NOT account signing certificates or private keys.
