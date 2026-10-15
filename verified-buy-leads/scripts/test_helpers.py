"""Offline regression checks: store integrity and HTTP failure handling."""
import csv
import copy
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from fetch_public import fetch
from lead_store import update, validate, record_status
from source_policy import source_kind
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
                        pain_point='仓库湿度过高',
                        solution_pitch='仓库潮湿 → 工业除湿机可能改善；需核实面积和温度')
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
            run_state.finish(directory, first['run_started_at'], 'partial', '')
            self.assertEqual(run_state.start(directory)['mode'], 'first')
            run_state.finish(directory, first['run_started_at'], 'ok', '')
            daily = run_state.start(directory)
            self.assertEqual((daily['mode'], daily['since']), ('daily', first['run_started_at']))
            update(directory, [sample()])
            run_state.mark(directory, [{'source_url': 'https://forum.example.com/t/9?utm_source=x', 'outcome': 'rejected'}])
            result = run_state.check(directory, [
                'http://www.example.com/rfq/1/',
                'https://forum.example.com/t/9?utm_source=feed',
                'https://forum.example.com/t/10?page=2',
                'https://forum.example.com/t/10?page=2#top',
            ])
            self.assertEqual(result['new'], ['https://forum.example.com/t/10?page=2'])
            self.assertEqual(len(result['seen']), 3)
            with self.assertRaises(ValueError):
                run_state.mark(directory, [{'source_url': 'https://example.com/x', 'outcome': 'maybe'}])

    def test_partitions_and_free_contact_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            base = sample()
            base.update(supply_route='direct', contact_path='free-direct', source_kind='forum', access_context='public',
                        contacts=[dict(type='website', value='Business contact form',
                                       source_url='https://example.com/contact', confidence='high')],
                        contact_path_evidence=dict(source_url='https://example.com/contact',
                                                   observation='Public business inquiry form, no payment required',
                                                   checked_at='2026-10-15T12:00:00+08:00'))
            active = copy.deepcopy(base)
            active.update(priority='A', validity='open', identity_confidence='high', fit='matched')
            validate(active)
            invalid = copy.deepcopy(active)
            invalid.pop('contact_path_evidence')
            with self.assertRaises(ValueError):
                validate(invalid)
            records = [active]
            for number, changes in enumerate([
                {'need_level': 'possible'}, {'contact_path': 'unknown'},
                {'supply_route': 'partner-only'}, {'validity': 'closed'},
                {'validity': 'expired'}, {'fit': 'mismatch'},
            ]):
                row = copy.deepcopy(base)
                row.update(changes, stable_key=f'test:{number+2}')
                records.append(row)
            update(directory, records)
            def count(name):
                with (directory / name).open(encoding='utf-8-sig', newline='') as stream:
                    return len(list(csv.DictReader(stream)))
            self.assertEqual([count(n) for n in ['leads.csv', 'review.csv', 'history.csv']], [1, 3, 3])
            self.assertEqual(len(json.loads((directory / 'leads.json').read_text(encoding='utf-8'))), 7)
            # Legacy A lacks new evidence: retain its audit record but do not export as active.
            legacy = copy.deepcopy(active)
            legacy.pop('contact_path_evidence')
            (directory / 'leads.json').write_text(json.dumps([legacy]), encoding='utf-8')
            update(directory, [])
            self.assertEqual(count('leads.csv'), 0)
            self.assertEqual(count('review.csv'), 1)

    def test_b2b_and_paid_sources_cannot_be_delivered(self):
        base = sample()
        base.update(source_kind='social', source_url='https://www.facebook.com/groups/test/posts/1',
                    access_context='public', supply_route='direct', contact_path='free-direct',
                    contacts=[dict(type='email', value='business@example.com', confidence='high',
                                   source_url='https://example.com/contact')],
                    contact_path_evidence=dict(source_url='https://example.com/contact',
                                               observation='Public business email, no payment',
                                               checked_at='2026-10-15T12:00:00Z'))
        self.assertEqual(record_status(base), 'active')
        records = [base]
        for number, url in enumerate(['https://rfq.alibaba.com/1',
                                      'https://www.go4worldbusiness.com/buyoffer/2',
                                      'https://govttenders.co.in/3']):
            row = copy.deepcopy(base)
            row.update(stable_key=f'excluded:{number}', source_url=url)
            self.assertEqual(record_status(row), 'excluded')
            records.append(row)
        paid = copy.deepcopy(base)
        paid.update(stable_key='paid', contact_path='paywalled')
        self.assertEqual(record_status(paid), 'excluded')
        records.append(paid)
        # Unlisted marketplaces must be classified by the reviewer.
        other = copy.deepcopy(base)
        other.update(source_url='https://new-market.example/rfq', source_kind='b2b-marketplace')
        self.assertEqual(record_status(other), 'excluded')
        # A domain containing the word alibaba is not the actual marketplace.
        other.update(source_url='https://alibaba.com.example.org/topic', source_kind='forum')
        self.assertEqual(source_kind(other), 'forum')
        with tempfile.TemporaryDirectory() as raw:
            update(raw, records)
            def rows(name):
                with (Path(raw) / name).open(encoding='utf-8-sig', newline='') as stream:
                    return list(csv.DictReader(stream))
            self.assertEqual(len(rows('leads.csv')), 1)
            self.assertEqual(len(rows('excluded.csv')), 4)
            self.assertEqual(rows('review.csv'), [])
            # Known blocked domains also migrate out of legacy A records.
            old = copy.deepcopy(records[1])
            old.update(priority='A', validity='open', identity_confidence='high', fit='matched')
            (Path(raw) / 'leads.json').write_text(json.dumps([old]), encoding='utf-8')
            update(raw, [])
            self.assertEqual(rows('leads.csv'), [])
            self.assertEqual(len(rows('excluded.csv')), 1)

    def test_registration_and_contact_source_guards(self):
        row = sample()
        row.update(source_kind='forum', supply_route='direct', contact_path='free-registration',
                   contacts=[dict(type='platform', value='Business inquiry', confidence='medium',
                                  source_url='https://example.com/contact')],
                   contact_path_evidence=dict(source_url='https://example.com/contact',
                                              observation='Free inquiry permission observed',
                                              checked_at='2026-10-15T12:00:00Z'))
        self.assertEqual(record_status(row), 'review')
        row['access_context'] = 'registration-required'
        self.assertEqual(record_status(row), 'review')
        row['access_context'] = 'existing-authorized-account'
        self.assertEqual(record_status(row), 'active')
        row['contact_path_evidence']['source_url'] = 'https://rfq.alibaba.com/contact'
        self.assertEqual(record_status(row), 'review')
        row['contact_path_evidence']['source_url'] = 'https://example.com/contact'
        row['contacts'][0]['source_url'] = 'https://www.tradekey.com/contact'
        self.assertEqual(record_status(row), 'review')
        row['contacts'][0]['source_url'] = 'https://example.com/contact'
        row['source_kind'] = 'unknown'
        self.assertEqual(record_status(row), 'review')

    def test_comments_business_parameters_and_revisit(self):
        self.assertNotEqual(run_state.normalize('https://example.com/p#comment-1'),
                            run_state.normalize('https://example.com/p#comment-2'))
        self.assertNotEqual(run_state.normalize('https://example.com/p?ref=buyer1'),
                            run_state.normalize('https://example.com/p?ref=buyer2'))
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            url = 'https://example.com/p#comment-1'
            run_state.mark(directory, [dict(source_url=url, outcome='lead', review_after='2000-01-01T00:00:00Z')])
            self.assertEqual(run_state.check(directory, [url])['revisit'], [url])
            run_state.mark(directory, [dict(source_url=url, outcome='lead', review_after='2099-01-01T00:00:00Z')])
            self.assertEqual(run_state.check(directory, [url])['seen'], [url])
            with self.assertRaises(ValueError):
                run_state.mark(directory, [dict(source_url=url, outcome='lead', review_after='2026-01-01')])

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
