"""Offline tests; no live profiles, model keys or paid calls."""
import json
import asyncio
import os
import sys
import subprocess
import socket
from pathlib import Path
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from bitbrowser import BitBrowser, local_url
from jobs import Jobs
from jev_bridge import browser_class, load_isolated, summary
from sessions import Sessions
from types import SimpleNamespace


class Checks(unittest.TestCase):
    def test_endpoint_restrictions(self):
        for url in ('http://example.com', 'file:///tmp/test', 'http://user:pass@localhost'):
            with self.assertRaises(ValueError):
                local_url(url, {'http'})
        self.assertEqual(local_url('ws://127.0.0.1:9000/devtools/browser/1', {'ws'}),
                         'ws://127.0.0.1:9000/devtools/browser/1')

    def test_bit_api_and_allowlist(self):
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append((self.path, payload))
                data = {'list': [{'id': 'allowed', 'name': 'Demo', 'cookie': 'secret'}, {'id': 'other'}]}
                if self.path == '/browser/open':
                    data = {'ws': 'ws://127.0.0.1:9000/devtools/browser/test'}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'success': True, 'data': data}).encode())

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            api = BitBrowser(f'http://127.0.0.1:{server.server_port}', ['allowed'])
            rows = api.list_profiles()
            self.assertEqual(rows, [{'id': 'allowed', 'name': 'Demo', 'seq': None}])
            with self.assertRaises(ValueError):
                api.open('other')
            self.assertEqual(len(calls), 1)
            api.open('allowed')
            self.assertEqual(calls[-1][1], {'id': 'allowed', 'ignoreDefaultUrls': True})
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_jobs_busy_cancel_and_validation(self):
        started = threading.Event()
        release = threading.Event()

        def runner(profile, url, goal, steps, budget, cancelled, progress):
            started.set()
            progress({'steps': 1})
            release.wait(2)
            return {'status': 'cancelled' if cancelled.is_set() else 'done', 'verification': 'required'}

        jobs = Jobs(runner, ['allowed'])
        try:
            for kwargs in [dict(profile_id='other'), dict(url='file:///tmp'), dict(max_steps=0)]:
                values = dict(profile_id='allowed', url='https://example.com', goal='Read page')
                values.update(kwargs)
                with self.assertRaises(ValueError):
                    jobs.submit(**values)
            job = jobs.submit('allowed', 'https://example.com', 'Read page')
            self.assertTrue(started.wait(1))
            with self.assertRaises(ValueError):
                jobs.submit('allowed', 'https://example.com', 'Read again')
            self.assertEqual(jobs.get(job['job_id'])['progress']['steps'], 1)
            self.assertEqual(jobs.cancel(job['job_id'])['status'], 'cancelling')
            release.set()
            deadline = time.monotonic() + 2
            while jobs.get(job['job_id'])['status'] == 'cancelling' and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(jobs.get(job['job_id'])['status'], 'cancelled')
        finally:
            release.set()
            jobs.pool.shutdown(wait=True)

    def test_upstream_bridge_isolation_and_owned_target_cleanup(self):
        import jev_ultrafast
        from jev_bridge import browser_class, load_isolated
        first = load_isolated(jev_ultrafast, 'browser')
        second = load_isolated(jev_ultrafast, 'browser')
        calls = []

        def connection(method, session_id=None, **params):
            calls.append((method, params))
            if method == 'Target.createTarget':
                return {'targetId': 'owned-tab'}
            if method == 'Target.attachToTarget':
                return {'sessionId': 'session'}
            if method == 'Runtime.evaluate':
                return {'result': {'value': 'complete'}}
            return {}

        original = second.cdp
        browser = browser_class(first, connection)('https://example.com')
        browser.close()
        browser.close()
        self.assertIs(second.cdp, original)
        self.assertEqual([p for m, p in calls if m == 'Target.closeTarget'], [{'targetId': 'owned-tab'}])
        self.assertFalse(any(m.startswith('Emulation.') for m, p in calls))
        self.assertNotIn('Browser.close', [m for m, p in calls])

    def test_real_jev_agent_with_fake_browser_and_policy(self):
        import jev_ultrafast
        from jev_bridge import load_isolated, summary
        agent_module = load_isolated(jev_ultrafast, 'agent')

        class FakeBrowser:
            def __init__(self, url):
                pass

            def observe(self, screenshot=False):
                return {'fingerprint': 'f', 'url': 'https://example.com', 'title': 'Example',
                        'text': 'Independent verification evidence', 'actions': []}

            def fresh(self, page, action=None):
                return True

            def close(self):
                pass

        agent_module.Browser = FakeBrowser
        agent_module.choose = lambda *args: {'choice': 'DONE', 'probabilities': {'DONE': 1}}
        agent = agent_module.Agent('https://example.com', 'Read page')
        agent.command('tick')
        self.assertEqual(summary(agent)['jev_status'], 'done')
        self.assertEqual(summary(agent)['verification'], 'required')
        agent.close()

    def test_mcp_stdio_handshake_and_config_errors(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def check():
            env = dict(os.environ, BITBROWSER_ALLOWED_PROFILES='test', TYPESAFE_API_KEY='', TEXT_MODEL_API_KEY='')
            params = StdioServerParameters(command=sys.executable,
                                          args=['-X', 'utf8', '-B', str(Path(__file__).with_name('server.py'))], env=env)
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    self.assertEqual({tool.name for tool in listed.tools},
                                     {'environment_check', 'list_profiles', 'submit_goal', 'get_job', 'cancel_job',
                                      'open_session', 'observe', 'click', 'fill', 'select', 'scroll', 'wait',
                                      'navigate', 'press_key', 'list_tabs', 'switch_tab', 'screenshot', 'close_session',
                                      'new_tab', 'browser_history', 'read_page'})
                    result = await session.call_tool('environment_check', {})
                    self.assertFalse(result.isError)
                    body = json.loads(result.content[0].text)
                    self.assertFalse(body['ready'])
                    self.assertTrue(body['step_ready'])
                    self.assertFalse(body['goal_ready'])
                    self.assertEqual(body['missing_credentials'], ['TYPESAFE_API_KEY'])
                    self.assertEqual(body['missing_optional_credentials'], ['TEXT_MODEL_API_KEY'])
                    self.assertIn('请在本机', body['credential_setup_prompt'])
                    rejected = await session.call_tool('submit_goal', {
                        'profile_id': 'test', 'url': 'https://example.com', 'goal': 'Read page'})
                    self.assertTrue(rejected.isError)
        asyncio.run(check())

    def test_manual_sessions_replay_snapshots_and_tab_ownership(self):
        class Stale(ValueError):
            pass

        calls = []

        class Browser:
            target = 'owned'
            session = 's1'

            def observe(self, screenshot=False):
                return {'url': 'https://example.com', 'title': 'Example', 'text': 'Read me',
                        'actions': [{'id': 'e1', 'kind': 'click', 'node': 1},
                                    {'id': 'e2', 'kind': 'fill', 'node': 2},
                                    {'id': 'e3', 'kind': 'select', 'node': 3, 'value': 'option'},
                                    {'id': 'scroll_down', 'kind': 'scroll', 'delta': 560},
                                    {'id': 'wait', 'kind': 'wait'}]}

            def act(self, action, page, text=None):
                calls.append(('act', action['kind'], text))

            def fresh(self, page):
                return True

            def call(self, method, **params):
                calls.append((method, params))
                if method == 'Page.captureScreenshot':
                    return {'data': 'aW1hZ2U='}
                if method == 'Page.getNavigationHistory':
                    return {'currentIndex': 1, 'entries': [{'id': 10}, {'id': 20}]}
                return {}

        class Connection:
            new_created = False

            def __call__(self, method, **params):
                calls.append((method, params))
                if method == 'Target.getTargets':
                    return {'targetInfos': [{'targetId': 'owned', 'type': 'page'},
                                             {'targetId': 'user', 'type': 'page'}] +
                            ([{'targetId': 'new', 'type': 'page'}] if self.new_created else [])}
                if method == 'Target.createTarget':
                    self.new_created = True
                    return {'targetId': 'new'}
                if method == 'Target.attachToTarget':
                    return {'sessionId': 's2'}
                return {}

            def close(self):
                calls.append(('disconnect',))

        manager = Sessions(SimpleNamespace(allowed={'p'}), lambda *args: (Browser(), Connection(), Stale))
        with self.assertRaises(ValueError):
            manager.open('other', 'https://example.com')
        sid = manager.open('p', 'https://example.com')['session_id']
        page = manager.observe(sid)
        args = (sid, page['snapshot_id'], 'e1', 'click', 'r1')
        self.assertEqual(manager.act(*args)['status'], 'executed')
        self.assertTrue(manager.act(*args)['replay'])
        self.assertEqual(len([c for c in calls if c[0] == 'act']), 1)
        with self.assertRaises(ValueError):
            manager.act(sid, page['snapshot_id'], 'e1', 'click', 'r2')
        with self.assertRaises(ValueError):
            manager.act(sid, page['snapshot_id'], 'e2', 'fill', 'r1', 'different')
        page = manager.observe(sid)
        self.assertEqual(manager.act(sid, page['snapshot_id'], 'e2', 'fill', 'r3', 'AI supplied')['status'], 'executed')
        self.assertIn(('act', 'fill', 'AI supplied'), calls)
        page = manager.observe(sid)
        self.assertEqual(manager.act(sid, page['snapshot_id'], 'missing', 'click', 'r4')['status'], 'rejected')
        page = manager.observe(sid)
        self.assertEqual(manager.act(sid, page['snapshot_id'], 'e3', 'select', 'r5')['status'], 'executed')
        page = manager.observe(sid)
        self.assertEqual(manager.navigate(sid, page['snapshot_id'], 'https://example.com/next', 'r6')['status'], 'executed')
        self.assertIn(('Page.navigate', {'url': 'https://example.com/next'}), calls)
        page = manager.observe(sid)
        self.assertEqual(manager.press_key(sid, page['snapshot_id'], 'Enter', 'r7')['status'], 'executed')
        self.assertEqual(len([c for c in calls if c[0] == 'Input.dispatchKeyEvent']), 2)
        self.assertEqual(manager.screenshot(sid), b'image')
        page = manager.observe(sid)
        self.assertEqual(manager.history(sid, page['snapshot_id'], 'back', 'r8')['status'], 'executed')
        self.assertIn(('Page.navigateToHistoryEntry', {'entryId': 10}), calls)
        page = manager.observe(sid)
        self.assertEqual(manager.new_tab(sid, page['snapshot_id'], 'https://example.com/tab', 'r9')['status'], 'executed')
        manager.switch_tab(sid, 'user')
        self.assertFalse(manager.tabs(sid)['tabs'][1]['owned'])
        manager.close(sid)
        closed = [c[1]['targetId'] for c in calls if c[0] == 'Target.closeTarget']
        self.assertEqual(set(closed), {'owned', 'new'})
        self.assertEqual(manager.close(sid)['status'], 'already_closed')

    def test_read_page_scrolls_dedupes_and_stops(self):
        class Browser:
            target = 'owned'
            session = 's1'
            y = 0
            screens = ['Header\nReview A', 'Review A\nReview B', 'Review B\nFooter']
            sent = []

            def observe(self, screenshot=False):
                index = min(self.y // 500, 2)
                return {'url': 'https://example.com/p', 'title': 'P', 'text': self.screens[index],
                        'scroll': {'y': min(self.y, 1000), 'height': 1600},
                        'actions': [{'id': 'e1', 'kind': 'click'},
                                    {'id': 'scroll_up', 'kind': 'scroll', 'delta': -560},
                                    {'id': 'scroll_down', 'kind': 'scroll', 'delta': 500}]}

            def act(self, action, page, text=None):
                if not self.sent:
                    self.sent.append('stale')
                    raise ValueError('Page changed')
                self.sent.append(action['id'])
                self.y += action['delta']

        class Connection:
            def __call__(self, method, **params):
                return {}

            def close(self):
                pass

        browser = Browser()
        manager = Sessions(SimpleNamespace(allowed={'p'}), lambda *args: (browser, Connection(), ValueError))
        sid = manager.open('p', 'https://example.com/p')['session_id']
        snapshot = manager.observe(sid)['snapshot_id']
        result = manager.read_page(sid)
        self.assertEqual(result['text'], 'Header\nReview A\nReview B\nFooter')
        self.assertTrue(result['end_reached'])
        self.assertFalse(result['truncated'])
        self.assertEqual(browser.sent[0], 'stale')
        self.assertEqual(set(browser.sent[1:]), {'scroll_down'})
        with self.assertRaises(ValueError):
            manager.act(sid, snapshot, 'e1', 'click', 'r1')
        browser.y = 0
        self.assertEqual(manager.read_page(sid, max_scrolls=0)['scrolls'], 0)
        with self.assertRaises(ValueError):
            manager.read_page(sid, max_scrolls=500)

    def test_manual_unknown_outcome_is_never_replayed(self):
        class Stale(ValueError):
            pass

        inputs = []

        class Browser:
            target = 'owned'
            session = 's'

            def observe(self, screenshot=False):
                return {'actions': [{'id': 'e1', 'kind': 'click'}]}

            def act(self, action, page, text=None):
                inputs.append(action)
                raise TimeoutError('input may have reached browser')

        class Connection:
            def __call__(self, *args, **kwargs):
                return {}

            def close(self):
                pass

        manager = Sessions(SimpleNamespace(allowed={'p'}), lambda *args: (Browser(), Connection(), Stale))
        sid = manager.open('p', 'https://example.com')['session_id']
        snap = manager.observe(sid)['snapshot_id']
        self.assertEqual(manager.act(sid, snap, 'e1', 'click', 'once')['status'], 'outcome_unknown')
        self.assertTrue(manager.act(sid, snap, 'e1', 'click', 'once')['replay'])
        self.assertEqual(len(inputs), 1)
        manager.close(sid)

    def test_mcp_streamable_http_handshake(self):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        env = dict(os.environ, BITBROWSER_ALLOWED_PROFILES='', TYPESAFE_API_KEY='', TEXT_MODEL_API_KEY='')
        process = subprocess.Popen(
            [sys.executable, '-X', 'utf8', '-B', str(Path(__file__).with_name('server.py')),
             '--transport', 'streamable-http', '--port', str(port)],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

        async def check():
            async with streamable_http_client(f'http://127.0.0.1:{port}/mcp') as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool('environment_check', {})
                    self.assertFalse(result.isError)

        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    self.fail('HTTP MCP process exited before startup')
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                        break
                except OSError:
                    time.sleep(0.1)
            asyncio.run(check())
        finally:
            process.terminate()
            process.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
