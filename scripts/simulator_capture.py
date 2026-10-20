import json
from pathlib import Path
import subprocess
import time

def call(*args):
    return subprocess.check_output(['xcrun', 'simctl', *args], text=True)

devices = json.loads(call('list', 'devices', 'available', '--json'))['devices']
candidates = [(runtime, device) for runtime, group in devices.items() if 'iOS' in runtime
              for device in group if device.get('isAvailable') and 'iPhone' in device['name']]
if not candidates:
    raise SystemExit('No available iPhone simulator')
_, device = sorted(candidates, key=lambda item: item[0], reverse=True)[0]
identifier = device['udid']
if device['state'] != 'Booted':
    call('boot', identifier)
call('bootstatus', identifier, '-b')
app = Path('build/simulator/Build/Products/Debug-iphonesimulator/InstallProbe.app').resolve()
call('install', identifier, str(app))
call('launch', identifier, 'site.shrks.kaspiprobe.install')
time.sleep(3)
call('io', identifier, 'screenshot', str(Path('output/install-probe.png').resolve()))
call('terminate', identifier, 'site.shrks.kaspiprobe.install')
call('shutdown', identifier)
print('Simulator launch and screenshot complete')
