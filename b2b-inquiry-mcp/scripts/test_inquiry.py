"""Offline tests; no BitBrowser windows, platform accounts or model calls."""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ledger import Ledger  # noqa: E402
from roles import load_config  # noqa: E402
from runner import Runner  # noqa: E402


class Clock:
    def __init__(self):
        self.value = datetime(2026, 10, 15, 2, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += timedelta(seconds=seconds)


class FakeSessions:
    def __init__(self):
        self.calls = []

    def open(self, profile_id, url):
        self.calls.append(('open', profile_id, url))
        return {'session_id': 's1'}

    def close(self, session_id):
        self.calls.append(('close', session_id))
        return {'status': 'closed'}

    def act(self, session_id, snapshot_id, action_id, kind, request_id, text=None):
        self.calls.append(('act', action_id, kind, request_id))
        return {'status': 'rejected' if action_id == 'missing' else 'executed', 'request_id': request_id}


def write_config(directory, **extra):
    path = Path(directory) / 'config.json'
    data = {'roles': {'1688_buyer': {'profile_id': 'p-buyer'}, 'alibaba_seller': {'profile_id': 'p-seller'}},
            'limits': {'buyer_daily_messages': 2, 'min_send_interval_seconds': 60, 'max_send_interval_seconds': 60},
            'buyer_goal': {'products': ['LED screen P3.91']}}
    data.update(extra)
    path.write_text(json.dumps(data), encoding='utf-8')
    return path


class Checks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.clock = Clock()
        self.ledger = Ledger(Path(self.temp.name) / 'ledger.sqlite3', now=self.clock)
        self.config = load_config(write_config(self.temp.name))
        self.sessions = FakeSessions()
        self.runner = Runner(self.config, self.ledger, self.sessions)

    def tearDown(self):
        self.ledger.db.close()
        self.temp.cleanup()

    def test_config_defaults_and_validation(self):
        roles = self.config['roles']
        self.assertEqual(set(roles), {'1688_buyer', '1688_seller', 'alibaba_buyer', 'alibaba_seller'})
        self.assertEqual(roles['1688_buyer']['profile_id'], 'p-buyer')
        self.assertEqual(roles['1688_seller']['profile_id'], '')
        self.assertEqual(self.config['limits']['recontact_days'], 14)
        bad = write_config(self.temp.name, limits={'min_send_interval_seconds': 10, 'max_send_interval_seconds': 5})
        with self.assertRaises(ValueError):
            load_config(bad)

    def test_run_requires_configured_role_and_is_exclusive(self):
        with self.assertRaises(ValueError):
            self.runner.start('1688_seller')
        with self.assertRaises(ValueError):
            self.runner.start('taobao_buyer')
        with self.assertRaises(ValueError):
            self.runner.session_id()
        brief = self.runner.start('1688_buyer', 'Find LED screen suppliers')
        self.assertEqual(brief['buyer_goal'], {'products': ['LED screen P3.91']})
        self.assertIn(('open', 'p-buyer', 'https://www.1688.com/'), self.sessions.calls)
        with self.assertRaises(ValueError):
            self.runner.start('alibaba_seller')
        self.assertEqual(self.runner.end()['status'], 'ended')
        self.assertIn(('close', 's1'), self.sessions.calls)
        self.assertEqual(self.runner.end()['status'], 'no_active_run')

    def test_send_guards_replay_interval_duplicate_and_cap(self):
        self.runner.start('1688_buyer')
        first = self.runner.send('snap', 'e9', 'r1', 'Factory A', 'Hello, price for P3.91?', 'P3.91')
        self.assertEqual(first['ledger_status'], 'sent_unverified')
        self.assertTrue(self.runner.send('snap', 'e9', 'r1', 'Factory A', 'Hello, price for P3.91?', 'P3.91')['replay'])
        self.assertEqual(len([c for c in self.sessions.calls if c[0] == 'act']), 1)
        self.assertEqual(self.runner.send('snap', 'e9', 'r2', 'Factory B', 'Hi', 'P3.91')['status'], 'too_soon')
        self.clock.advance(61)
        self.assertEqual(self.runner.send('snap', 'e9', 'r3', 'Factory A', 'Hi again', 'P3.91')['status'],
                         'duplicate_inquiry')
        rejected = self.runner.send('snap', 'missing', 'r4', 'Factory B', 'Hi', 'P3.91')
        self.assertFalse(rejected['recorded'])
        self.assertTrue(self.runner.send('snap', 'e9', 'r5', 'Factory B', 'Hi', 'P3.91')['recorded'])
        self.clock.advance(61)
        self.assertEqual(self.runner.send('snap', 'e9', 'r6', 'Factory C', 'Hi', 'P3.91')['status'],
                         'daily_limit_reached')
        self.assertEqual(len([c for c in self.sessions.calls if c[0] == 'act']), 3)
        self.ledger.set_status(first['message_id'], 'sent')
        with self.assertRaises(ValueError):
            self.ledger.set_status(9999, 'sent')

    def test_stats_reply_rate_wait_quotes_and_export(self):
        self.runner.start('1688_buyer')
        self.runner.send('snap', 'e9', 'r1', 'Factory A', 'Price?', 'P3.91')
        self.clock.advance(1800)
        reply = self.runner.record_inbound('Factory A', '¥980/㎡, MOQ 10', 'P3.91',
                                           fields={'price': '980', 'currency': 'CNY', 'moq': '10', 'evil': 'x'})
        self.assertFalse(reply['duplicate'])
        self.assertTrue(self.runner.record_inbound('Factory A', '¥980/㎡, MOQ 10', 'P3.91')['duplicate'])
        self.clock.advance(60)
        self.runner.send('snap', 'e9', 'r2', 'Factory B', 'Price?', 'P3.91')
        stats = self.runner.end()['run_stats']
        self.assertEqual(stats['counterparts_contacted'], 2)
        self.assertEqual(stats['counterparts_replied'], 1)
        self.assertEqual(stats['reply_rate'], 0.5)
        self.assertEqual(stats['median_first_reply_minutes'], 30.0)
        self.assertEqual(stats['awaiting_their_reply'], 1)
        self.assertEqual(stats['awaiting_our_reply'], 1)
        self.assertEqual(stats['quotes'][0]['moq'], '10')
        self.assertNotIn('evil', stats['quotes'][0])
        exported = self.ledger.export_csv(Path(self.temp.name) / 'exports', '1688_buyer', 30)
        self.assertEqual(exported['rows'], 3)
        self.assertTrue(Path(exported['path']).read_text(encoding='utf-8-sig').startswith('role,counterpart'))

    def test_mcp_stdio_handshake(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def check():
            env = dict(os.environ, B2B_INQUIRY_CONFIG=str(write_config(self.temp.name)),
                       B2B_INQUIRY_DATA=str(Path(self.temp.name) / 'data'))
            params = StdioServerParameters(command=sys.executable,
                                           args=['-X', 'utf8', '-B', str(Path(__file__).with_name('server.py'))],
                                           env=env)
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    names = {tool.name for tool in (await session.list_tools()).tools}
                    self.assertTrue({'list_roles', 'start_run', 'end_run', 'send_message', 'record_inbound',
                                     'get_stats', 'export_csv', 'observe', 'fill', 'read_page'} <= names)
                    roles = json.loads((await session.call_tool('list_roles', {})).content[0].text)
                    self.assertEqual(len(roles['roles']), 4)
                    rejected = await session.call_tool('observe', {})
                    self.assertTrue(rejected.isError)
                    enter = await session.call_tool('press_key', {'snapshot_id': 'x', 'key': 'Enter',
                                                                  'request_id': 'r'})
                    self.assertTrue(enter.isError)
        asyncio.run(check())


if __name__ == '__main__':
    unittest.main()
