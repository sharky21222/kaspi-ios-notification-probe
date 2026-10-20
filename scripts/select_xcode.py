import os
from pathlib import Path
import re
import subprocess

candidates = []
for path in Path('/Applications').glob('Xcode*.app'):
    developer = path / 'Contents/Developer'
    env = {**os.environ, 'DEVELOPER_DIR': str(developer)}
    result = subprocess.run(['xcodebuild', '-version'], env=env, capture_output=True, text=True)
    match = re.search(r'Xcode (\d+(?:\.\d+)*)', result.stdout)
    if result.returncode == 0 and match:
        candidates.append((tuple(int(part) for part in match[1].split('.')), developer))
if not candidates:
    raise SystemExit('No Xcode installation found')
version, path = max(candidates)
if version < (26, 5):
    raise SystemExit('Accessory Notifications requires an SDK from Xcode 26.5 or newer')
with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as output:
    output.write('DEVELOPER_DIR=' + str(path) + '\n')
print('Selected Xcode', '.'.join(map(str, version)))
