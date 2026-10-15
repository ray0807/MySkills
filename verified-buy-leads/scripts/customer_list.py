"""Build one user-facing list from current discoveries and earlier review records."""
import argparse
import csv
import io
import json
from pathlib import Path
from lead_store import atomic_write, record_status
from run_state import normalize
from source_policy import excluded_reason
from time_policy import freshness, policy


def export_customers(data_dir):
    directory = Path(data_dir)
    sources = []
    for filename in ('candidates.json', 'leads.json'):
        path = directory / filename
        if path.exists():
            rows = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(rows, list):
                raise ValueError(f'{filename} must be an array')
            sources.extend((filename, row) for row in rows)
    # Import old split files only when their corresponding JSON master is absent.
    legacy_names = {'review', 'leads', 'candidate-links', 'discovery-links', 'candidate', 'discovery'}
    aliases = {'source_url': ['链接', '原帖链接'], 'buyer': ['客户或作者', '客户/作者', '名称'],
               'product': ['产品'], 'need_excerpt': ['需求摘要', '标题或需求摘要'],
               'title': ['标题', '说明'], 'query': ['搜索词'], 'published_at': ['发布日期'],
               'found_at': ['发现时间'], 'next_step': ['备注']}
    for path in sorted(directory.glob('*.csv')):
        stem = path.stem.lower()
        candidate_file = stem in {'candidate-links', 'discovery-links', 'candidate', 'discovery'} or stem.startswith(('待核验', '发现入口'))
        lead_file = stem in {'review', 'leads'} or stem.startswith('可跟进')
        if not (candidate_file or lead_file or stem in legacy_names):
            continue
        master = 'candidates.json' if candidate_file else 'leads.json'
        if (directory / master).exists():
            continue
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for raw in csv.DictReader(stream):
                row = dict(raw)
                for field, labels in aliases.items():
                    if not row.get(field):
                        row[field] = next((raw[label] for label in labels if raw.get(label)), '')
                sources.append((path.name, row))
    indexed = {}
    time_settings = policy(directory)
    for filename, row in sources:
        url = row.get('source_url', '')
        if not url or excluded_reason(row):
            continue
        key = normalize(url)
        time_status = freshness(row, max_days=time_settings['max_post_age_days'])
        if time_status == '超期历史':
            indexed[key] = (100, None)
            continue
        if row.get('validity') in {'closed', 'expired'} or row.get('fit') == 'mismatch':
            # The later reviewed record supersedes a stale discovery at the same URL.
            indexed[key] = (100, None)
            continue
        reviewed = filename == 'leads.json' and record_status(row) == 'active'
        text = row.get('need_excerpt') or row.get('excerpt') or ''
        kind = '需求线索' if text else '发现入口'
        rank = 30 if reviewed else (20 if text else 10)
        result = {
            '类型': kind, '客户或作者': row.get('buyer') or row.get('author') or '',
            '产品': row.get('product', ''), '标题或需求摘要': text or row.get('title', ''),
            '链接': key, '状态': '已核验可跟进' if reviewed else '待核验',
            '发布日期': row.get('published_at', ''),
            '时效': time_status,
            '发现时间': row.get('first_found_at') or row.get('found_at') or row.get('first_seen_at', ''),
            '搜索词': row.get('query') or row.get('keyword') or '',
            '备注': '原帖、时效及联系权限未核验' if filename == 'candidates.json' else row.get('next_step', '历史待核验记录'),
        }
        old_rank, old = indexed.get(key, (0, None))
        if old_rank > rank:
            if old:
                for field, value in result.items():
                    if not old.get(field):
                        old[field] = value
            continue
        if old:
            for field, value in old.items():
                if not result.get(field):
                    result[field] = value
        indexed[key] = (rank, result)
    rows = [row for rank, row in sorted(indexed.values(), key=lambda item: -item[0]) if row]
    fields = ['类型', '客户或作者', '产品', '标题或需求摘要', '链接', '状态', '发布日期', '时效', '发现时间', '搜索词', '备注']
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: "'" + value if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')) else value
                         for key, value in row.items()})
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write(directory / '客户名单.csv', output.getvalue(), 'utf-8-sig')
    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True)
    args = parser.parse_args()
    try:
        print(f'Exported {export_customers(args.data_dir)} rows to 客户名单.csv')
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(1, f'Customer list failed: {error}\n')
