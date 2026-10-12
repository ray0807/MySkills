"""Bounded local BitBrowser API and synchronous CDP connection."""
import json
import threading
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def local_url(value, schemes):
    parsed = urlparse(value)
    if parsed.scheme not in schemes or parsed.hostname not in {'localhost', '127.0.0.1', '::1'} or parsed.username:
        raise ValueError('Only local BitBrowser/CDP endpoints are supported')
    return value


class BitBrowser:
    def __init__(self, base_url='http://127.0.0.1:54345', allowed_profiles=()):
        self.base_url = local_url(base_url.rstrip('/'), {'http', 'https'})
        self.allowed = frozenset(allowed_profiles)

    def request(self, path, payload):
        request = Request(self.base_url + path, data=json.dumps(payload).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        if result.get('success') is not True:
            raise RuntimeError('BitBrowser rejected request; check local API and profile permissions')
        return result.get('data')

    def list_profiles(self, page=0, page_size=20):
        if not 0 <= page or not 1 <= page_size <= 100:
            raise ValueError('Invalid pagination')
        data = self.request('/browser/list', {'page': page, 'pageSize': page_size})
        rows = data.get('list', []) if isinstance(data, dict) else []
        return [{'id': row['id'], 'name': row.get('name', ''), 'seq': row.get('seq')}
                for row in rows if row.get('id') in self.allowed]

    def open(self, profile_id):
        if profile_id not in self.allowed:
            raise ValueError('Profile is not in BITBROWSER_ALLOWED_PROFILES')
        data = self.request('/browser/open', {'id': profile_id, 'ignoreDefaultUrls': True})
        if not isinstance(data, dict) or not data.get('ws'):
            raise RuntimeError('BitBrowser did not return data.ws')
        return local_url(data['ws'], {'ws', 'wss'})


class CDP:
    def __init__(self, endpoint):
        from websocket import create_connection
        self.socket = create_connection(local_url(endpoint, {'ws', 'wss'}), timeout=30, suppress_origin=True)
        self.counter = 0
        self.lock = threading.Lock()

    def __call__(self, method, session_id=None, **params):
        with self.lock:
            self.counter += 1
            message = {'id': self.counter, 'method': method, 'params': params}
            if session_id:
                message['sessionId'] = session_id
            self.socket.send(json.dumps(message))
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                self.socket.settimeout(max(0.01, deadline - time.monotonic()))
                response = json.loads(self.socket.recv())
                if response.get('id') != self.counter:
                    continue
                if 'error' in response:
                    raise RuntimeError(f'CDP {method} failed: {response["error"].get("message", "unknown")}')
                return response.get('result', {})
            raise TimeoutError('CDP response timeout; mutation outcome may be unknown')

    def close(self):
        self.socket.close()
