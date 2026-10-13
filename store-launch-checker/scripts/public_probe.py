"""Bounded public evidence collection, not a complete browser or launch verdict."""
import argparse
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import socket
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

AGENT = 'StoreLaunchChecker/1.0'
HEADERS = ('content-type', 'x-robots-tag', 'strict-transport-security', 'content-security-policy',
           'x-content-type-options', 'referrer-policy', 'permissions-policy', 'cache-control')
ACTION_PATH = re.compile(r'(?:logout|signout|unsubscribe|delete|remove|add-to-cart|checkout|order|payment)', re.I)


def valid_url(url):
    p = urlsplit(url)
    if p.scheme not in {'http', 'https'} or not p.hostname or p.username or p.password:
        raise ValueError('Supply an HTTP(S) URL without embedded credentials')
    return urlunsplit((p.scheme, p.netloc, p.path or '/', p.query, ''))


class Document(HTMLParser):
    def __init__(self, url):
        super().__init__(convert_charrefs=True)
        self.url = url
        self.title = ''
        self.h1_count = 0
        self.meta = {}
        self.canonical = []
        self.hreflang = []
        self.links = []
        self.images = []
        self.json_ld = []
        self._title = False
        self._ld = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'title':
            self._title = True
        if tag == 'h1':
            self.h1_count += 1
        if tag == 'meta':
            key = (a.get('name') or a.get('property') or '').lower()
            if key:
                self.meta.setdefault(key, []).append(a.get('content', ''))
        if tag == 'link':
            rel = a.get('rel', '').lower().split()
            if 'canonical' in rel:
                self.canonical.append(urljoin(self.url, a.get('href', '')))
            if a.get('hreflang'):
                self.hreflang.append({'language': a['hreflang'], 'url': urljoin(self.url, a.get('href', ''))})
        if tag == 'a' and a.get('href'):
            self.links.append(urljoin(self.url, a['href']))
        if tag == 'img':
            source = a.get('src') or a.get('data-src')
            self.images.append({'url': urljoin(self.url, source) if source else None,
                                'alt': a.get('alt'), 'loading': a.get('loading'), 'srcset': a.get('srcset')})
        if tag == 'script' and a.get('type', '').lower() == 'application/ld+json':
            self._ld = ''

    def handle_data(self, value):
        if self._title:
            self.title += value
        if self._ld is not None:
            self._ld += value

    def handle_endtag(self, tag):
        if tag == 'title':
            self._title = False
        if tag == 'script' and self._ld is not None:
            try:
                self.json_ld.append({'syntax': 'valid', 'data': json.loads(self._ld)})
            except ValueError:
                self.json_ld.append({'syntax': 'invalid'})
            self._ld = None

    def evidence(self):
        return {k: getattr(self, k) for k in ('title', 'h1_count', 'meta', 'canonical', 'hreflang',
                                            'links', 'images', 'json_ld')}


class ScopeRedirect(HTTPRedirectHandler):
    def __init__(self, within):
        self.within = within

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not self.within(newurl):
            raise ValueError('Cross-scope redirect; inspect with browser/explicitly configured target')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Probe:
    def __init__(self, root, max_requests=40, delay=0.25):
        self.root = valid_url(root)
        host = urlsplit(self.root).hostname
        bare = host[4:] if host.startswith('www.') else host
        self.hosts = {bare, 'www.' + bare}
        self.ports = {urlsplit(self.root).port, 80, 443, None}
        self.max_requests = max_requests
        self.delay = delay
        self.count = 0
        self.stopped = False
        self.opener = build_opener(ScopeRedirect(self.within))

    def within(self, url):
        try:
            p = urlsplit(valid_url(url))
            return p.hostname in self.hosts and p.port in self.ports
        except ValueError:
            return False

    def fetch(self, url):
        url = valid_url(url)
        if not self.within(url):
            return {'url': url, 'outcome': 'out_of_scope'}, ''
        if self.stopped or self.count >= self.max_requests:
            return {'url': url, 'outcome': 'budget_or_rate_limit'}, ''
        if self.count:
            time.sleep(self.delay)
        self.count += 1
        started = time.perf_counter()
        result = {'url': url, 'observed_at': datetime.now(timezone.utc).isoformat()}
        try:
            req = Request(url, headers={'User-Agent': AGENT, 'Accept-Encoding': 'identity'})
            try:
                response = self.opener.open(req, timeout=10)
            except HTTPError as error:
                response = error
            with response:
                result.update(status=response.code, final_url=response.url,
                              headers={k: response.headers[k] for k in HEADERS if k in response.headers})
                raw = response.read(1024 * 1024 + 1)
                result['truncated'] = len(raw) > 1024 * 1024
                result['http_elapsed_ms'] = round((time.perf_counter() - started) * 1000)
                result['outcome'] = ('blocked' if response.code in {401, 403, 429} else
                                     'http_error' if response.code >= 400 else 'received')
                if response.code == 429:
                    self.stopped = True
                    result['retry_after'] = response.headers.get('Retry-After')
                text = raw[:1024 * 1024].decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
                if any(marker in text.lower() for marker in ('cf-chl-', 'verify you are human', 'just a moment...')):
                    result['outcome'] = 'challenge'
                return result, text
        except (URLError, OSError, ValueError, LookupError) as error:
            result.update(outcome='fetch_error', error_type=type(error).__name__)
            return result, ''


def tls_evidence(url):
    p = urlsplit(url)
    if p.scheme != 'https':
        return {'status': 'not_https', 'note': 'Browser must confirm expected redirect/production HTTPS'}
    try:
        with socket.create_connection((p.hostname, p.port or 443), timeout=10) as connection:
            with ssl.create_default_context().wrap_socket(connection, server_hostname=p.hostname) as secure:
                certificate = secure.getpeercert()
                expiry = ssl.cert_time_to_seconds(certificate['notAfter'])
                return {'status': 'verified', 'expires_at': datetime.fromtimestamp(expiry, timezone.utc).isoformat(),
                        'days_remaining': int((expiry - time.time()) / 86400), 'tls_version': secure.version()}
    except (OSError, ValueError, KeyError) as error:
        return {'status': 'verification_error', 'error_type': type(error).__name__}


def collect(url, seed_pages=(), max_pages=12, max_requests=40, delay=0.25, check_images=False):
    if not 1 <= max_pages <= 100 or not 3 <= max_requests <= 200 or not 0 <= delay <= 10:
        raise ValueError('Use 1–100 pages, 3–200 requests, and 0–10 seconds delay')
    probe = Probe(url, max_requests, delay)
    origin = urlunsplit((*urlsplit(probe.root)[:2], '/', '', ''))
    robots, robots_text = probe.fetch(urljoin(origin, 'robots.txt'))
    parser = RobotFileParser()
    parser.parse(robots_text.splitlines() if robots.get('status') == 200 else [])
    sitemap, sitemap_text = probe.fetch(urljoin(origin, 'sitemap.xml'))
    if sitemap.get('status') == 200:
        try:
            tree = ET.fromstring(sitemap_text)
            sitemap['root_type'] = tree.tag.split('}')[-1]
            sitemap['sample_urls'] = [node.text for node in tree.iter() if node.tag.split('}')[-1] == 'loc'][:30]
            sitemap['xml_syntax'] = 'valid'
        except ET.ParseError:
            sitemap['xml_syntax'] = 'invalid'
    queue = deque([probe.root, *(valid_url(page) for page in seed_pages)])
    explicit = set(queue)
    visited = set()
    pages = []
    assets = []
    while queue and len(pages) < max_pages and not probe.stopped and probe.count < max_requests:
        page_url = queue.popleft()
        if page_url in visited:
            continue
        visited.add(page_url)
        if robots.get('status') == 200 and page_url not in explicit and not parser.can_fetch(AGENT, page_url):
            pages.append({'url': page_url, 'outcome': 'robots_skipped'})
            continue
        response, text = probe.fetch(page_url)
        if response['outcome'] == 'received' and 'html' in response.get('headers', {}).get('content-type', '').lower():
            doc = Document(response.get('final_url', page_url))
            doc.feed(text)
            response['html'] = doc.evidence()
            for link in doc.links:
                p = urlsplit(link)
                if probe.within(link) and not p.query and not ACTION_PATH.search(p.path):
                    if not p.path.lower().endswith(('.pdf', '.zip', '.png', '.jpg', '.webp', '.svg')):
                        queue.append(valid_url(link))
            if check_images:
                for image in doc.images:
                    link = image['url']
                    if not link or any(a['url'] == link for a in assets):
                        continue
                    if not probe.within(link):
                        assets.append({'url': link, 'outcome': 'external_asset_not_tested'})
                    else:
                        evidence, _ = probe.fetch(link)
                        assets.append(evidence)
        pages.append(response)
    return {'site_url': probe.root, 'checked_at': datetime.now(timezone.utc).isoformat(),
            'method': 'public_http_source_html', 'request_count': probe.count, 'robots': robots, 'sitemap': sitemap,
            'tls': tls_evidence(probe.root), 'pages': pages, 'image_requests': assets,
            'limits': ['sampled source HTML, not JS-rendered DOM', 'http_elapsed_ms is not LCP or TTFB',
                       'no payment, order, email, inventory, analytics or legal compliance verification',
                       'no external link/CDN crawl; images are HTTP checks, not visual checks',
                       'max requests excludes redirect hops and the single TLS handshake',
                       'explicit seeds inspected even if robots blocks them; discovered URLs respect robots',
                       'sitemap index/gzip and alternate locations need follow-up; never a launch verdict']}


if __name__ == '__main__':
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--url', required=True)
    args.add_argument('--page', action='append', default=[])
    args.add_argument('--max-pages', type=int, default=12)
    args.add_argument('--max-requests', type=int, default=40)
    args.add_argument('--delay', type=float, default=0.25)
    args.add_argument('--check-images', action='store_true')
    args.add_argument('--output', required=True)
    options = args.parse_args()
    try:
        result = collect(options.url, options.page, options.max_pages, options.max_requests, options.delay,
                         options.check_images)
        target = Path(options.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Evidence saved: {target.resolve()} ({result["request_count"]} requests). No launch verdict.')
    except (ValueError, OSError) as error:
        args.exit(1, f'Probe could not complete: {type(error).__name__}\n')
