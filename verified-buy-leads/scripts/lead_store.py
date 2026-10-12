"""Validate and upsert reviewed leads; Python 3 standard library only."""
import argparse
import csv
import io
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ENUMS = {
    'need_level': {'explicit', 'possible'},
    'validity': {'open', 'closed', 'expired', 'unknown'},
    'confirmation': {'public-unconfirmed', 'buyer-confirmed'},
    'identity_confidence': {'high', 'medium', 'low', 'unknown'},
    'fit': {'matched', 'partial', 'mismatch', 'unknown'},
    'priority': {'A', 'B', 'C'},
}


def check_url(value):
    if not isinstance(value, str):
        raise ValueError('URL must be a string')
    parsed = urlparse(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username:
        raise ValueError('Invalid public source URL')


def check_time(value):
    if not isinstance(value, str) or datetime.fromisoformat(value.replace('Z', '+00:00')).utcoffset() is None:
        raise ValueError('Timestamp must include timezone')


def validate(row):
    if not isinstance(row, dict):
        raise ValueError('Each lead must be an object')
    for key in ('stable_key', 'buyer', 'country', 'product', 'need_excerpt'):
        if not isinstance(row.get(key), str):
            raise ValueError(f'{key} must be a string')
    if not row['stable_key'].strip() or not row['need_excerpt'].strip():
        raise ValueError('stable_key and need_excerpt cannot be empty')
    check_url(row.get('source_url'))
    check_time(row.get('last_verified_at'))
    for key, allowed in ENUMS.items():
        if row.get(key) not in allowed:
            raise ValueError(f'Invalid {key}')
    if not isinstance(row.get('contacts'), list):
        raise ValueError('contacts must be an array')
    for contact in row['contacts']:
        if not isinstance(contact, dict):
            raise ValueError('Each contact must be an object')
        if contact.get('type') not in {'email', 'phone', 'whatsapp', 'linkedin', 'website', 'platform'}:
            raise ValueError('Invalid contact type')
        if not isinstance(contact.get('value'), str) or not contact['value'].strip():
            raise ValueError('Missing contact value')
        if contact.get('confidence') not in {'high', 'medium', 'low', 'unknown'}:
            raise ValueError('Invalid contact confidence')
        check_url(contact.get('source_url'))
    if row['confirmation'] == 'buyer-confirmed':
        if not row.get('confirmation_evidence'):
            raise ValueError('Buyer confirmation requires evidence')
        check_time(row.get('confirmation_at'))
    if row['priority'] == 'A' and not (
        row['need_level'] == 'explicit' and row['validity'] == 'open'
        and row['identity_confidence'] == 'high' and row['fit'] == 'matched'
        and any(c['confidence'] == 'high' for c in row['contacts'])
    ):
        raise ValueError('A priority requires explicit/open/high/matched and a high confidence contact')


def atomic_write(path, content, encoding='utf-8'):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.lead-store-')
    try:
        with os.fdopen(fd, 'w', encoding=encoding, newline='') as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def update(data_dir, incoming):
    if not isinstance(incoming, list):
        raise ValueError('Input must be a JSON array')
    for row in incoming:
        validate(row)
    if len({r['stable_key'] for r in incoming}) != len(incoming):
        raise ValueError('Duplicate stable_key in input')
    directory = Path(data_dir)
    master = directory / 'leads.json'
    existing = json.loads(master.read_text(encoding='utf-8')) if master.exists() else []
    if not isinstance(existing, list):
        raise ValueError('Existing store is not an array')
    for row in existing:
        validate(row)
    if len({r['stable_key'] for r in existing}) != len(existing):
        raise ValueError('Existing store contains duplicate keys')
    indexed = {r['stable_key']: r for r in existing}
    now = datetime.now(timezone.utc).isoformat()
    next_id = max((r.get('lead_id', 0) for r in existing), default=0) + 1
    history = []
    for raw in incoming:
        row = dict(raw)
        old = indexed.get(row['stable_key'])
        if old:
            history.append({'archived_at': now, 'record': old})
        row['lead_id'] = old['lead_id'] if old else next_id
        row['first_seen_at'] = old['first_seen_at'] if old else now
        row['updated_at'] = now
        indexed[row['stable_key']] = row
        if not old:
            next_id += 1
    rows = list(indexed.values())
    directory.mkdir(parents=True, exist_ok=True)
    if history:
        with (directory / 'history.jsonl').open('a', encoding='utf-8') as stream:
            for item in history:
                stream.write(json.dumps(item, ensure_ascii=False) + '\n')
    atomic_write(master, json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    fields = ['lead_id', 'stable_key', 'buyer', 'country', 'product', 'priority',
              'validity', 'confirmation', 'source_url', 'last_verified_at']
    fields += sorted({k for row in rows for k in row} - set(fields))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        safe = {}
        for key, value in row.items():
            value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
            # Treat spreadsheet formula-like source text as text in the CSV export.
            if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
                value = "'" + value
            safe[key] = value
        writer.writerow(safe)
    atomic_write(directory / 'leads.csv', output.getvalue(), 'utf-8-sig')
    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--input', help='Reviewed leads JSON array (full records)')
    args = parser.parse_args()
    try:
        incoming = json.loads(Path(args.input).read_text(encoding='utf-8-sig')) if args.input else []
        print(f'Stored {update(args.data_dir, incoming)} leads in {Path(args.data_dir).resolve()}')
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(1, f'Lead store failed: {error}\n')
