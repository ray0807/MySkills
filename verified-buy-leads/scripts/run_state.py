"""Track daily runs and deduplicate candidate URLs; Python 3 standard library only.

start   Print the search window: first run, or daily run since the last completed run.
check   Split candidate URLs into new and already seen.
mark    Record handled candidates (lead, signal or rejected) so later runs skip them.
finish  Record a completed run; the next daily window starts from its start time.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from lead_store import check_time, check_url

TRACKING = {'fbclid', 'gclid', 'mc_cid', 'mc_eid', 'ref_src', 'igshid', 'si'}
OUTCOMES = {'lead', 'signal', 'rejected'}
RUN_STATUSES = {'ok', 'partial', 'failed'}


def normalize(url):
    check_url(url)
    parsed = urlparse(url.strip())
    host = parsed.hostname.lower()
    if host.startswith('www.'):
        host = host[4:]
    netloc = host + (f':{parsed.port}' if parsed.port else '')
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
             if not (k.lower().startswith('utm_') or k.lower() in TRACKING)]
    path = parsed.path.rstrip('/') or '/'
    return urlunparse(('https' if parsed.scheme in {'http', 'https'} else parsed.scheme,
                       netloc, path, '', urlencode(sorted(query)), '' if parsed.fragment.lower() in {'top', 'topofpage'} else parsed.fragment))


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def append_jsonl(path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as stream:
        for item in items:
            stream.write(json.dumps(item, ensure_ascii=False) + '\n')


def seen_urls(directory):
    seen = set()
    master = directory / 'leads.json'
    if master.exists():
        for row in json.loads(master.read_text(encoding='utf-8')):
            seen.add(normalize(row['source_url']))
    for name in ('seen.jsonl', 'signals.jsonl'):
        for item in read_jsonl(directory / name):
            if item.get('source_url'):
                seen.add(normalize(item['source_url']))
    return seen


def start(directory):
    now = datetime.now(timezone.utc)
    completed = [r for r in read_jsonl(directory / 'runs.jsonl') if r.get('status') == 'ok']
    if not completed:
        return {'mode': 'first', 'since': None, 'run_started_at': now.isoformat()}
    last = max(completed, key=lambda r: datetime.fromisoformat(r['run_started_at'].replace('Z', '+00:00')))
    return {'mode': 'daily', 'since': last['run_started_at'], 'run_started_at': now.isoformat()}


def check(directory, urls):
    if not isinstance(urls, list):
        raise ValueError('Input must be a JSON array of URLs')
    seen = seen_urls(directory)
    latest = {}
    master = directory / 'leads.json'
    if master.exists():
        for item in json.loads(master.read_text(encoding='utf-8')):
            latest[normalize(item['source_url'])] = item.get('next_review_at')
    for item in read_jsonl(directory / 'seen.jsonl'):
        latest[normalize(item['source_url'])] = item.get('review_after')
    now = datetime.now(timezone.utc)
    due = {key for key, value in latest.items() if value and
           datetime.fromisoformat(value.replace('Z', '+00:00')) <= now}
    result, batch = {'new': [], 'seen': [], 'revisit': []}, set()
    for url in urls:
        key = normalize(url)
        bucket = 'seen' if key in batch else ('revisit' if key in due else ('seen' if key in seen else 'new'))
        result[bucket].append(url)
        batch.add(key)
    return result


def mark(directory, items):
    if not isinstance(items, list):
        raise ValueError('Input must be a JSON array')
    now = datetime.now(timezone.utc).isoformat()
    records = []
    for item in items:
        if not isinstance(item, dict) or item.get('outcome') not in OUTCOMES:
            raise ValueError('Each item needs outcome lead, signal or rejected')
        if item.get('review_after'):
            check_time(item['review_after'])
        records.append({'review_after': item.get('review_after'), 'source_url': normalize(item.get('source_url')), 'outcome': item['outcome'],
                        'reason': item.get('reason', ''), 'marked_at': now})
    append_jsonl(directory / 'seen.jsonl', records)
    return len(records)


def finish(directory, started_at, status, summary):
    check_time(started_at)
    if status not in RUN_STATUSES:
        raise ValueError('status must be ok, partial or failed')
    record = {'run_started_at': started_at, 'finished_at': datetime.now(timezone.utc).isoformat(),
              'status': status, 'summary': summary}
    append_jsonl(directory / 'runs.jsonl', [record])
    return record


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['start', 'check', 'mark', 'finish'])
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--input', help='JSON file: URL array for check, item array for mark')
    parser.add_argument('--started-at', help='run_started_at returned by start')
    parser.add_argument('--status', default='ok')
    parser.add_argument('--summary', default='')
    args = parser.parse_args()
    directory = Path(args.data_dir)
    try:
        if args.command == 'start':
            output = start(directory)
        elif args.command == 'check':
            output = check(directory, load(args.input))
        elif args.command == 'mark':
            output = {'marked': mark(directory, load(args.input))}
        else:
            output = finish(directory, args.started_at, args.status, args.summary)
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(1, f'Run state failed: {error}\n')
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)
