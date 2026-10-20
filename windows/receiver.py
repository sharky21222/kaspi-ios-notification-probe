"""Local synthetic connectivity probe. No donation API or bank notification ingestion."""

import argparse
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import ipaddress
import json
import secrets
import socket
import threading
import time
import uuid

SERVICE_UUID = '5cc0c4ab-2d7f-4b59-b527-0d867e11fd10'


class ProbeServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, address, token, ttl=900):
        self.token = token
        self.deadline = time.monotonic() + ttl
        self.received = set()
        super().__init__(address, ProbeHandler)
        self.timeout = .5


class ProbeHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(3)

    def log_message(self, *_args):
        pass

    def reply(self, code, payload):
        data = json.dumps(payload).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.reply(404, {'ok': False})

    def do_POST(self):
        if self.path != '/probe' or self.headers.get('Origin'):
            return self.reply(404, {'ok': False})
        address = ipaddress.ip_address(self.client_address[0])
        if not address.is_private or time.monotonic() >= self.server.deadline:
            return self.reply(403, {'ok': False})
        expected = 'Bearer ' + self.server.token
        if not hmac.compare_digest(self.headers.get('Authorization', '').encode(), expected.encode()):
            return self.reply(401, {'ok': False})
        try:
            length = int(self.headers.get('Content-Length', '-1'))
            if not 1 <= length <= 256 or self.headers.get_content_type() != 'application/json':
                raise ValueError('invalid body')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or set(payload) != {'kind', 'nonce'} or payload['kind'] != 'connectivity-test':
                raise ValueError('only synthetic tests are allowed')
            nonce = str(uuid.UUID(payload['nonce']))
            if len(self.server.received) >= 1024 and nonce not in self.server.received:
                return self.reply(429, {'ok': False})
        except (ValueError, TypeError, KeyError, UnicodeError):
            return self.reply(400, {'ok': False})
        fresh = nonce not in self.server.received
        self.server.received.add(nonce)
        if fresh:
            print('Synthetic connectivity check received; no bank data.', flush=True)
        self.reply(200, {'ok': True, 'nonce': nonce})


async def advertise(stop):
    import asyncio
    from winrt.windows.devices.bluetooth import BluetoothAdapter, BluetoothError
    from winrt.windows.devices.bluetooth.genericattributeprofile import (
        GattCharacteristicProperties, GattLocalCharacteristicParameters, GattProtectionLevel,
        GattServiceProvider, GattServiceProviderAdvertisingParameters,
    )
    from winrt.windows.storage.streams import DataWriter

    adapter = await BluetoothAdapter.get_default_async()
    if adapter is None or not adapter.is_peripheral_role_supported:
        raise RuntimeError('Bluetooth peripheral role is unavailable')
    result = await GattServiceProvider.create_async(uuid.UUID(SERVICE_UUID))
    if result.error != BluetoothError.SUCCESS:
        raise RuntimeError('Could not create the test GATT service: ' + result.error.name)
    provider = result.service_provider
    parameters = GattLocalCharacteristicParameters()
    parameters.characteristic_properties = GattCharacteristicProperties.READ
    parameters.read_protection_level = GattProtectionLevel.PLAIN
    writer = DataWriter()
    try:
        writer.write_bytes(b'kaspi-probe/1;capability-test-only')
        parameters.static_value = writer.detach_buffer()
    finally:
        writer.close()
    characteristic = await provider.service.create_characteristic_async(
        uuid.UUID('5cc0c4ab-2d7f-4b59-b527-0d867e11fd11'), parameters)
    if characteristic.error != BluetoothError.SUCCESS:
        raise RuntimeError('Could not create the read-only test characteristic')
    options = GattServiceProviderAdvertisingParameters()
    options.is_connectable = True
    options.is_discoverable = True
    try:
        provider.start_advertising(options)
        print('BLE capability-test accessory is discoverable. No notification transport is implemented.', flush=True)
        while not stop.is_set():
            await asyncio.sleep(.25)
    finally:
        provider.stop_advertising()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, help='Private IPv4 address of this PC')
    parser.add_argument('--port', type=int, default=5127)
    parser.add_argument('--minutes', type=int, default=15, choices=range(1, 31))
    parser.add_argument('--advertise', action='store_true', help='Publish a separate read-only BLE test service')
    args = parser.parse_args()
    address = ipaddress.ip_address(args.host)
    if address.version != 4 or not address.is_private or address.is_unspecified:
        parser.error('--host must be this PC\'s private IPv4 address')
    token = secrets.token_hex(32)
    stop = threading.Event()
    worker = None
    if args.advertise:
        def run_advertiser():
            import asyncio
            try:
                asyncio.run(advertise(stop))
            except Exception as error:
                print('BLE probe unavailable: ' + type(error).__name__ + ': ' + str(error), flush=True)
        worker = threading.Thread(target=run_advertiser, daemon=True)
        worker.start()
    try:
        with ProbeServer((args.host, args.port), token, args.minutes * 60) as server:
            print('IPv4:', args.host, flush=True)
            print('Key:', token, flush=True)
            print('Expires in', args.minutes, 'minutes. Ctrl+C stops this test.', flush=True)
            while time.monotonic() < server.deadline:
                server.handle_request()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        if worker:
            worker.join(timeout=2)


if __name__ == '__main__':
    main()
