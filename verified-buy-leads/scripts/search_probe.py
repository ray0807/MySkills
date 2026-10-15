"""Assess actual search result URLs; offline helper, not a search engine client."""
import argparse
import json
from urllib.parse import parse_qs, urlparse
from lead_store import atomic_write, check_time, check_url
from pathlib import Path


def result_url(value):
    check_url(value)
    parsed = urlparse(value)
    host = (parsed.hostname or '').lower()
    # Only unwrap known search redirect formats, never arbitrary query strings.
    params = parse_qs(parsed.query)
    key = 'uddg' if host in {'duckduckgo.com', 'www.duckduckgo.com'} else None
    if host in {'google.com', 'www.google.com'} and parsed.path == '/url':
        key = 'q' if 'q' in params else 'url'
    if key and params.get(key):
        check_url(params[key][0])
        return params[key][0]
    return value


def assess(probe):
    if not isinstance(probe, dict):
        raise ValueError('Each probe must be an object')
    for key in ('provider', 'query', 'target_domain'):
        if not isinstance(probe.get(key), str) or not probe[key].strip():
            raise ValueError(f'{key} is required')
    check_time(probe.get('checked_at'))
    domain = probe['target_domain'].lower().rstrip('.')
    if any(char in domain for char in '/:@ ') or '.' not in domain:
        raise ValueError('target_domain must be a hostname')
    urls = probe.get('result_urls')
    if not isinstance(urls, list):
        raise ValueError('result_urls must be an array of actual returned links')
    unique, invalid = set(), 0
    for value in urls:
        try:
            unique.add(result_url(value))
        except (ValueError, TypeError):
            invalid += 1
    matched = sum((urlparse(url).hostname or '').lower().rstrip('.') == domain
                  or (urlparse(url).hostname or '').lower().rstrip('.').endswith('.' + domain)
                  for url in unique)
    total = len(unique)
    ratio = matched / total if total else 0
    state = probe.get('response_state', 'ok')
    if state not in {'ok', 'blocked', 'captcha', 'error'}:
        raise ValueError('Invalid response_state')
    if state != 'ok':
        status = state
    elif not total:
        status = 'inconclusive-empty'
    elif total < 5:
        status = 'inconclusive-small-sample'
    elif ratio >= 0.8:
        status = 'usable-sample'
    else:
        status = 'site-filter-unreliable'
    return dict(probe, status=status, sample_size=total, target_count=matched,
                target_ratio=round(ratio, 3), invalid_count=invalid,
                scope='search-link-discovery-only')


def assess_all(probes):
    if not isinstance(probes, list):
        raise ValueError('Input must be an array')
    return [assess(probe) for probe in probes]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', help='Internal JSON diagnostic, not a user deliverable')
    args = parser.parse_args()
    try:
        result = assess_all(json.loads(Path(args.input).read_text(encoding='utf-8-sig')))
        content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(target, content)
        print(content)
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(1, f'Search probe failed: {error}\n')
