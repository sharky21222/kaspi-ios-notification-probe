import importlib.util
import json
from pathlib import Path
import sys
import threading
import unittest
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'windows'))
from receiver import ProbeServer


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.server = ProbeServer(('127.0.0.1', 0), 'a' * 64)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def send(self, payload=None, token='a' * 64, path='/probe', headers=None):
        data = json.dumps(payload or {'kind': 'connectivity-test', 'nonce': str(uuid.uuid4())}).encode()
        req = urllib.request.Request(self.url + path, data=data,
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def test_synthetic_ping_echoes_nonce_and_deduplicates(self):
        payload = {'kind': 'connectivity-test', 'nonce': str(uuid.uuid4())}
        for _ in range(2):
            code, result = self.send(payload)
            self.assertEqual(code, 200)
            self.assertEqual(result['nonce'], payload['nonce'])
        self.assertEqual(len(self.server.received), 1)

    def test_wrong_key_and_expired_session(self):
        self.assertEqual(self.send(token='b' * 64)[0], 401)
        self.server.deadline = 0
        self.assertEqual(self.send()[0], 403)

    def test_donation_payload_and_unknown_fields_are_rejected(self):
        for payload in ({'kind': 'donation', 'nonce': str(uuid.uuid4())},
                        {'kind': 'connectivity-test', 'nonce': str(uuid.uuid4()), 'body': 'private'},
                        {'kind': 'connectivity-test', 'nonce': 'not-a-uuid'}):
            self.assertEqual(self.send(payload)[0], 400)
        self.assertEqual(len(self.server.received), 0)

    def test_unrelated_routes_and_browser_origins_rejected(self):
        self.assertEqual(self.send(path='/api/donations')[0], 404)
        self.assertEqual(self.send(headers={'Origin': 'https://example.invalid'})[0], 404)

    def test_oversized_body_rejected(self):
        self.assertEqual(self.send({'kind': 'connectivity-test', 'nonce': 'a' * 300})[0], 400)


if __name__ == '__main__': unittest.main()
