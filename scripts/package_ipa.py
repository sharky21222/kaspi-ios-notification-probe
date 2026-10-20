import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'output'
OUTPUT.mkdir(exist_ok=True)
manifest = {'commit': os.environ.get('GITHUB_SHA', ''), 'apple_signed': False,
            'bank_reception_verified': False, 'packages': []}
for name, filename in [('InstallProbe', 'Kaspi-Install-Probe.ipa'), ('AccessProbe', 'Kaspi-Access-Probe.ipa')]:
    source = ROOT / 'build/device/Build/Products/Release-iphoneos' / (name + '.app')
    staging = ROOT / 'build' / ('package-' + name)
    app = staging / 'Payload' / source.name
    if app.exists():
        raise SystemExit('Refusing to overwrite existing staging app: ' + str(app))
    app.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, app)
    extensions = list(app.glob('Extensions/*.appex')) + list(app.glob('PlugIns/*.appex'))
    if name == 'AccessProbe' and len(extensions) != 3:
        raise SystemExit('Capability IPA must contain all three extensions')
    for extension in extensions:
        entitlements = ROOT / 'build' / (extension.stem + '.entitlements')
        subprocess.run(['codesign', '--force', '--sign', '-', '--generate-entitlement-der',
                        '--entitlements', str(entitlements), str(extension)], check=True)
    # Ad-hoc signing preserves requested extension keys for the re-signing tool.
    # It is NOT an Apple-issued provisioning profile and cannot authorize an iPhone.
    subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    with (app / 'Info.plist').open('rb') as stream:
        info = plistlib.load(stream)
    target = OUTPUT / filename
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(staging.rglob('*')):
            if file.is_file():
                archive.write(file, file.relative_to(staging).as_posix())
    manifest['packages'].append({'file': filename, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                                 'bundle_id': info['CFBundleIdentifier'], 'extensions': len(extensions),
                                 'requires_resigning': True})
(OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps(manifest, indent=2))
