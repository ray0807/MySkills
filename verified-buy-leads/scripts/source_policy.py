"""Default source eligibility; classification is supplied by the reviewing agent."""
import json
from pathlib import Path
from urllib.parse import urlparse

POLICY = json.loads((Path(__file__).resolve().parent.parent / 'assets' / 'source-policy.json').read_text(encoding='utf-8'))
SOURCE_KINDS = {'social', 'forum', 'buyer-owned', 'official-procurement',
                'b2b-marketplace', 'lead-directory', 'paid-aggregator', 'unknown'}
EXCLUDED_KINDS = {'b2b-marketplace', 'lead-directory', 'paid-aggregator'}


def matches(host, domains):
    return any(host == domain or host.endswith('.' + domain) for domain in domains)


def source_kind(row):
    host = (urlparse(row.get('source_url', '')).hostname or '').lower().rstrip('.')
    if matches(host, POLICY['excluded_domains']):
        return 'b2b-marketplace'
    supplied = row.get('source_kind', 'unknown')
    if supplied in EXCLUDED_KINDS:
        return supplied
    if matches(host, POLICY['social_domains']):
        return 'social'
    return supplied


def excluded_reason(row):
    if source_kind(row) in EXCLUDED_KINDS:
        return 'excluded-source'
    if row.get('contact_path') == 'paywalled':
        return 'paid-contact'
    return ''


def eligible_source(row):
    return source_kind(row) in {'social', 'forum', 'buyer-owned', 'official-procurement'}
