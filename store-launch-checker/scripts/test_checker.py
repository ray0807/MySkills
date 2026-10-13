"""Offline fixtures verify evidence collection and conservative launch verdicts."""
import copy
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import unittest

from public_probe import collect, Document
from build_report import assess, render
from new_plan import create_plan


def sample_report():
    return {'site_url': 'https://example.com', 'checked_at': '2026-10-13T10:00:00+08:00',
            'environment': 'production', 'limitations': ['Sample only'],
            'planned_checks': [{'id': 'ENV-01', 'title': 'HTTPS', 'launch_gate': True},
                               {'id': 'PAY-03', 'title': 'Payment closed loop', 'launch_gate': True}],
            'checks': [{'id': 'ENV-01', 'status': 'pass', 'severity': 'high',
                        'evidence': [{'method': 'https', 'url': 'https://example.com', 'observation': 'TLS verified'}]}]}


class Checks(unittest.TestCase):
    def test_complete_plan_cannot_start_as_ready(self):
        ecommerce = create_plan('https://example.com', 'production')
        self.assertEqual(len(ecommerce['planned_checks']), 52)
        self.assertEqual(assess(ecommerce)['verdict'], 'verification_required')
        lead = create_plan('https://example.com', 'production', 'lead')
        self.assertEqual(len(lead['planned_checks']), 56)
        self.assertTrue(any(c['id'] == 'LEAD-03' and c['launch_gate'] for c in lead['planned_checks']))
        self.assertEqual(assess(lead)['verdict'], 'verification_required')

    def test_source_html_and_json_ld(self):
        doc = Document('https://example.com/product')
        doc.feed('<title>Glasses &amp; cases</title><h1>Glasses</h1><meta name="robots" content="noindex">'
                 '<link rel="canonical" href="/product"><img src="/image.png" alt="Glasses">'
                 '<script type="application/ld+json">{"@type":"Product"}</script>'
                 '<script type="application/ld+json">invalid</script>')
        self.assertEqual(doc.title, 'Glasses & cases')
        self.assertEqual(doc.canonical, ['https://example.com/product'])
        self.assertEqual(doc.json_ld[1]['syntax'], 'invalid')
        self.assertEqual(doc.meta['robots'], ['noindex'])

    def test_bounded_http_errors_robots_and_no_action_links(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                if self.path == '/robots.txt':
                    body = 'User-agent: *\nDisallow: /blocked\n'
                    status, content_type = 200, 'text/plain'
                elif self.path == '/sitemap.xml':
                    body = '<urlset><url><loc>https://example.com/product</loc></url></urlset>'
                    status, content_type = 200, 'application/xml'
                elif self.path == '/':
                    body = '<title>Store</title><a href="/missing">Missing</a><a href="/blocked">Private</a>'
                    body += '<a href="/logout">Logout</a><a href="/checkout">Checkout</a>'
                    status, content_type = 200, 'text/html'
                else:
                    body, status, content_type = 'Not found', 404, 'text/html'
                self.send_response(status)
                self.send_header('Content-Type', content_type)
                self.end_headers()
                self.wfile.write(body.encode())

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = collect(f'http://127.0.0.1:{server.server_port}', max_requests=8, delay=0)
            self.assertLessEqual(result['request_count'], 8)
            self.assertTrue(any(p.get('status') == 404 for p in result['pages']))
            self.assertTrue(any(p['outcome'] == 'robots_skipped' for p in result['pages']))
            self.assertNotIn('/blocked', requests)
            self.assertNotIn('/logout', requests)
            self.assertNotIn('/checkout', requests)
            self.assertEqual(result['sitemap']['xml_syntax'], 'valid')
            self.assertNotIn('verdict', result)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_missing_gate_is_not_pass(self):
        report = assess(sample_report())
        self.assertEqual(report['verdict'], 'verification_required')
        self.assertEqual(report['checks'][1]['status'], 'not_tested')
        self.assertEqual(report['coverage'], {'determinate': 1, 'applicable': 2})
        self.assertIn('不是健康评分', render(report))

    def test_gate_failure_and_scoped_ready(self):
        source = sample_report()
        source['checks'].append({'id': 'PAY-03', 'status': 'fail', 'severity': 'high',
                                 'launch_gate': False, 'evidence': [{'method': 'test-payment',
                                 'record_reference': 'test-order-1', 'observation': 'No backend order'}]})
        self.assertEqual(assess(source)['verdict'], 'blocked')
        source['checks'][1]['status'] = 'pass'
        self.assertEqual(assess(source)['verdict'], 'ready_in_scope')
        source['environment'] = 'unknown'
        self.assertEqual(assess(source)['verdict'], 'verification_required')

    def test_fabricated_pass_and_invalid_not_applicable_rejected(self):
        source = sample_report()
        source['checks'][0]['evidence'] = []
        with self.assertRaises(ValueError):
            assess(source)
        source = sample_report()
        source['checks'][0]['evidence'] = [{}]
        with self.assertRaises(ValueError):
            assess(source)
        source = sample_report()
        source['checks'][0]['status'] = 'not_applicable'
        with self.assertRaises(ValueError):
            assess(source)

    def test_optional_unknown_is_disclosed(self):
        source = sample_report()
        source['planned_checks'] = [source['planned_checks'][0], {'id': 'SEO-09', 'title': 'Social', 'launch_gate': False}]
        report = assess(source)
        self.assertEqual(report['verdict'], 'ready_with_issues')
        source['checks'].append(copy.deepcopy(source['checks'][0]))
        with self.assertRaises(ValueError):
            assess(source)


if __name__ == '__main__':
    unittest.main()
