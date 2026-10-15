"""Store discovered URLs without opening them; no network or third-party packages."""
import argparse
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from lead_store import atomic_write, check_time, check_url
from run_state import normalize
from source_policy import SOURCE_KINDS, excluded_reason, source_kind


def validate_candidate(row):
    if not isinstance(row, dict):
        raise ValueError('Candidate must be an object')
    check_url(row.get('source_url'))
    check_time(row.get('found_at'))
    for key in ('published_at_iso', 'published_observed_at'):
        if row.get(key):
            check_time(row[key])
    for key in ('product', 'query'):
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError(f'{key} is required')
    for key in ('title', 'excerpt', 'author', 'published_at', 'provider'):
        if key in row and not isinstance(row[key], str):
            raise ValueError(f'{key} must be a string (empty if unknown)')
    if row.get('source_kind', 'unknown') not in SOURCE_KINDS:
        raise ValueError('Invalid source_kind')
    if row.get('evidence_mode') not in {'search-snippet', 'indexed-text', 'link-only'}:
        raise ValueError('Invalid evidence_mode')
    if row['evidence_mode'] != 'link-only' and not row.get('excerpt', '').strip():
        raise ValueError('Text evidence requires a literal excerpt')
    if row['evidence_mode'] == 'link-only' and row.get('excerpt', '').strip():
        raise ValueError('Use a text evidence mode when an excerpt is available')


def category(row):
    if excluded_reason(row):
        return 'excluded'
    return 'candidate' if row.get('excerpt', '').strip() else 'discovery'


def update_candidates(data_dir, incoming, diagnostics=False):
    if not isinstance(incoming, list):
        raise ValueError('Input must be an array')
    directory = Path(data_dir)
    master = directory / 'candidates.json'
    existing = json.loads(master.read_text(encoding='utf-8')) if master.exists() else []
    if not isinstance(existing, list):
        raise ValueError('Existing candidates must be an array')
    for row in existing + incoming:
        validate_candidate(row)
    indexed = {normalize(row['source_url']): dict(row) for row in existing}
    now = datetime.now(timezone.utc).isoformat()
    for raw in incoming:
        key = normalize(raw['source_url'])
        old = indexed.get(key, {})
        row = dict(old)
        row.update(raw)
        if raw.get('published_at'):
            row['published_observed_at'] = raw.get('published_observed_at') or raw['found_at']
        elif old.get('published_at'):
            row['published_at'] = old['published_at']
            row['published_observed_at'] = old.get('published_observed_at') or old['found_at']
        # Rediscovering a bare URL must not erase earlier text evidence.
        if old.get('excerpt') and not raw.get('excerpt'):
            row['excerpt'] = old['excerpt']
            row['evidence_mode'] = old['evidence_mode']
        for field in ('title', 'author', 'published_at', 'provider'):
            if not row.get(field) and old.get(field):
                row[field] = old[field]
        row['source_url'] = key
        row['first_found_at'] = old.get('first_found_at', raw['found_at'])
        row['updated_at'] = now
        # These are collection records, regardless of any incoming claims.
        row.update(verification='unverified', validity='unknown', contact_path='unknown',
                   identity_confidence='unknown', confirmation='public-unconfirmed')
        row['source_kind'] = source_kind(row)
        row['record_status'] = category(row)
        row['exclusion_reason'] = excluded_reason(row)
        indexed[key] = row
    rows = list(indexed.values())
    # Recompute partitions for old records too; the master retains all discoveries.
    for row in rows:
        row.update(verification='unverified', validity='unknown', contact_path='unknown',
                   identity_confidence='unknown', confirmation='public-unconfirmed')
        row['source_kind'] = source_kind(row)
        row['record_status'] = category(row)
        row['exclusion_reason'] = excluded_reason(row)
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write(master, json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    fields = ['source_url', 'product', 'query', 'title', 'excerpt', 'evidence_mode',
              'author', 'published_at', 'found_at', 'verification', 'record_status']
    fields += sorted({key for row in rows for key in row} - set(fields))
    for status, filename in [('candidate', 'candidate-links.csv'), ('discovery', 'discovery-links.csv'),
                             ('excluded', 'excluded-candidates.csv')]:
        if not diagnostics:
            continue
        output = io.StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            if row['record_status'] != status:
                continue
            safe = {}
            for key, value in row.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
                    value = "'" + value
                safe[key] = value
            writer.writerow(safe)
        atomic_write(directory / filename, output.getvalue(), 'utf-8-sig')
    from customer_list import export_customers
    export_customers(directory)
    return {status: sum(row['record_status'] == status for row in rows)
            for status in ('candidate', 'discovery', 'excluded')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--input', help='JSON array of search discoveries; omit to rebuild exports')
    parser.add_argument('--diagnostics', action='store_true', help='Also export internal category CSVs')
    args = parser.parse_args()
    try:
        incoming = json.loads(Path(args.input).read_text(encoding='utf-8-sig')) if args.input else []
        print(json.dumps(update_candidates(args.data_dir, incoming, args.diagnostics), ensure_ascii=False))
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(1, f'Candidate store failed: {error}\n')
