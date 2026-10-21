"""Package only the signer, public source and license notices. No account data."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "signer/target/x86_64-pc-windows-msvc/release/kaspi-probe-signer.exe"
OUTPUT = ROOT / "output"


def main():
    if EXE.read_bytes()[:2] != b"MZ":
        raise ValueError("Expected a Windows executable")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    manifest = {
        "version": "0.1.0",
        "source_commit": commit,
        "executable_sha256": hashlib.sha256(EXE.read_bytes()).hexdigest(),
        "apple_credentials_in_build": False,
        "device_installation_tested": False,
        "bank_notifications_verified": False,
    }
    OUTPUT.mkdir(exist_ok=True)
    manifest_path = OUTPUT / "signer-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(OUTPUT / "Kaspi-Probe-Signer-Windows.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(EXE, "kaspi-probe-signer.exe")
        archive.write(ROOT / "signer/README.md", "README.md")
        archive.write(ROOT / "signer/THIRD_PARTY.md", "THIRD_PARTY.md")
        archive.write(ROOT / "signer/LICENSE", "LICENSE")
        archive.write(ROOT / "signer/vendor/isideload/LICENSE", "licenses/isideload-MIT.txt")
        archive.write(ROOT / "signer/vendor/apple-codesign-quick/LICENSE", "licenses/apple-codesign-quick-LGPL-2.1.txt")
        archive.write(ROOT / "build/signer-source.zip", "source.zip")
        archive.write(manifest_path, manifest_path.name)
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
