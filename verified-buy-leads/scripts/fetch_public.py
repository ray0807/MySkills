"""Fetch one public HTTP(S) page; failure is never reported as empty demand."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from lead_store import atomic_write, check_url


def fetch(url, output, timeout=30):
    check_url(url)
    report = {'url': url, 'fetched_at': datetime.now(timezone.utc).isoformat()}
    try:
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; PublicLeadResearch/1.0)'})
        with urlopen(request, timeout=timeout) as response:
            report.update(http_status=response.status, final_url=response.url)
            content_type = response.headers.get_content_type()
            if not (content_type.startswith('text/') or content_type in {'application/json', 'application/xhtml+xml', 'application/xml'}):
                raise ValueError('Non-text response; use a dedicated attachment download tool')
            body = response.read(5 * 1024 * 1024 + 1)
            if len(body) > 5 * 1024 * 1024:
                raise ValueError('Response exceeds 5 MiB; use a dedicated document tool')
            text = body.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
            lower = text.lower()
            if not body.strip():
                raise ValueError('Empty response')
            if any(marker in lower for marker in ('cf-chl-', 'verify you are human', 'just a moment...', 'captcha')):
                report['status'] = 'blocked'
                raise ValueError('Possible access challenge; inspect with browser')
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(path, text)
            report.update(status='ok', bytes=len(body), output=str(path.resolve()))
    except HTTPError as error:
        report.update(status='blocked' if error.code in (401, 403, 429) else 'error',
                      http_status=error.code, error=str(error), retry_after=error.headers.get('Retry-After'))
    except (URLError, OSError, ValueError, LookupError) as error:
        report.setdefault('status', 'error')
        report['error'] = str(error)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        result = fetch(args.url, args.output)
    except ValueError as error:
        result = {'status': 'error', 'error': str(error)}
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result['status'] == 'ok' else 1)
