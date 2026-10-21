"""Read public Xcode signing definitions only; never read account/profile stores."""
import json
import plistlib
import subprocess
from pathlib import Path

NEEDLES = (
    "accessory-data-provider",
    "accessory-transport-security",
    "accessory-transport-extension",
    "AccessoryNotifications",
)


def matching_records(value, path=()):
    if isinstance(value, dict):
        scalar_matches = any(
            any(needle in str(key) or (isinstance(item, str) and needle in item)
                for needle in NEEDLES)
            for key, item in value.items()
        )
        if scalar_matches:
            yield {"key_path": list(path), "definition": value}
        else:
            for key, item in value.items():
                yield from matching_records(item, path + (str(key),))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from matching_records(item, path + (str(index),))


def main():
    developer = Path(subprocess.check_output(["xcode-select", "-p"], text=True).strip())
    contents = developer.parent
    roots = [
        contents / "PlugIns",
        contents / "SharedFrameworks",
        contents / "Frameworks",
        developer / "Platforms/iPhoneOS.platform",
        developer / "Library/Xcode/Specifications",
    ]
    matches = []
    candidates = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            try:
                if not path.is_file():
                    continue
                if any(word in path.name.lower() for word in ("capabilit", "entitlement")):
                    candidates.append(str(path.relative_to(contents)))
                if path.suffix not in (".plist", ".entitlements", ".json", ".xml", ".xcspec", ".xcplugindata"):
                    continue
                resolved = path.resolve()
                if resolved in seen or path.stat().st_size > 16 * 1024 * 1024:
                    continue
                seen.add(resolved)
                raw = path.read_bytes()
                if not any(needle.encode() in raw for needle in NEEDLES):
                    continue
                try:
                    value = json.loads(raw) if path.suffix == ".json" else plistlib.loads(raw)
                    records = list(matching_records(value))
                except (ValueError, plistlib.InvalidFileException):
                    text = raw.decode("utf-8", errors="replace")
                    records = [{"matching_lines": [line for line in text.splitlines()
                        if any(needle in line for needle in NEEDLES)][:30]}]
                if records:
                    matches.append({"file": str(path.relative_to(contents)), "records": records})
            except (OSError, ValueError, plistlib.InvalidFileException):
                continue
    report = {
        "xcode": subprocess.check_output(["xcodebuild", "-version"], text=True).strip(),
        "account_accessed": False,
        "provisioning_profiles_read": False,
        "scanned_public_metadata_files": len(seen),
        "candidate_definition_files": sorted(set(candidates)),
        "matches": matches,
    }
    output = Path("output")
    output.mkdir(exist_ok=True)
    (output / "xcode-accessory-capabilities.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
