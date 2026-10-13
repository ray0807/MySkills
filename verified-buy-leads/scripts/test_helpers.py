"""Offline regression checks: store integrity and HTTP failure handling."""
import copy
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from fetch_public import fetch
from lead_store import update
import run_state


def sample():
    return dict(stable_key='test:1', buyer='测试买家', country='', product='护目镜',
                source_url='https://example.com/rfq/1', need_excerpt='Need goggles',
                need_level='explicit', validity='unknown', confirmation='public-unconfirmed',
                identity_confidence='unknown', fit='unknown', priority='B',
                last_verified_at='2026-10-12T12:00:00+08:00', contacts=[])


class Checks(unittest.TestCase):
    def test_initialize_upsert_and_reject_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(update(directory, []), 0)
            self.assertEqual(update(directory, [sample()]), 1)
            master = Path(directory) / 'leads.json'
            first = json.loads(master.read_text(encoding='utf-8'))[0]
            revised = sample()
            revised['quantity'] = 500
            update(directory, [revised])
            current = json.loads(master.read_text(encoding='utf-8'))[0]
            self.assertEqual(current['lead_id'], first['lead_id'])
            self.assertEqual(current['first_seen_at'], first['first_seen_at'])
            self.assertEqual(current['quantity'], 500)
            archived = json.loads((Path(directory) / 'history.jsonl').read_text(encoding='utf-8'))
            self.assertEqual(archived['record'], first)
            before = master.read_bytes()
            bad = copy.deepcopy(revised)
            bad['priority'] = 'A'
            with self.assertRaises(ValueError):
                update(directory, [bad])
            self.assertEqual(master.read_bytes(), before)
            bad = copy.deepcopy(revised)
            bad['confirmation'] = 'buyer-confirmed'
            with self.assertRaises(ValueError):
                update(directory, [bad])
            with self.assertRaises(ValueError):
                update(directory, [revised, revised])
            self.assertEqual(master.read_bytes(), before)

    def test_pain_leads_require_reasoning_and_fixed_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            pain = sample()
            pain.update(stable_key='test:pain', need_level='pain', pain_type='seeking',
                        pain_point='投影太暗看不清歌词',
                        solution_pitch='投影开灯后看不清歌词 → LED 屏高亮度，开灯也清晰')
            self.assertEqual(update(directory, [pain]), 1)
            master = Path(directory) / 'leads.json'
            before = master.read_bytes()
            for change in ({'priority': 'C'}, {'pain_type': 'complaint'}, {'pain_type': None},
                           {'solution_pitch': ' '}, {'priority': 'A'}):
                bad = copy.deepcopy(pain)
                bad.update(change)
                with self.assertRaises(ValueError):
                    update(directory, [bad])
            self.assertEqual(master.read_bytes(), before)
            complaint = copy.deepcopy(pain)
            complaint.update(pain_type='complaint', priority='C')
            self.assertEqual(update(directory, [complaint]), 1)

    def test_run_window_and_deduplication(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            first = run_state.start(directory)
            self.assertEqual(first['mode'], 'first')
            run_state.finish(directory, first['run_started_at'], 'failed', '')
            self.assertEqual(run_state.start(directory)['mode'], 'first')
            run_state.finish(directory, first['run_started_at'], 'ok', '')
            daily = run_state.start(directory)
            self.assertEqual((daily['mode'], daily['since']), ('daily', first['run_started_at']))
            update(directory, [sample()])
            run_state.mark(directory, [{'source_url': 'https://forum.example.com/t/9?utm_source=x', 'outcome': 'rejected'}])
            result = run_state.check(directory, [
                'http://www.example.com/rfq/1/',
                'https://forum.example.com/t/9?ref=feed',
                'https://forum.example.com/t/10?page=2',
                'https://forum.example.com/t/10?page=2#top',
            ])
            self.assertEqual(result['new'], ['https://forum.example.com/t/10?page=2'])
            self.assertEqual(len(result['seen']), 3)
            with self.assertRaises(ValueError):
                run_state.mark(directory, [{'source_url': 'https://example.com/x', 'outcome': 'maybe'}])

    def test_http_success_empty_blocked_and_missing(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(403 if self.path == '/blocked' else 200)
                self.end_headers()
                if self.path == '/ok':
                    self.wfile.write(b'<html>RFQ</html>')
                elif self.path == '/challenge':
                    self.wfile.write(b'Verify you are human')

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / 'page.html'
                url = f'http://127.0.0.1:{server.server_port}'
                self.assertEqual(fetch(url + '/ok', target)['status'], 'ok')
                original = target.read_bytes()
                for path, status in [('/empty', 'error'), ('/blocked', 'blocked'), ('/challenge', 'blocked')]:
                    self.assertEqual(fetch(url + path, target)['status'], status)
                    self.assertEqual(target.read_bytes(), original)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
