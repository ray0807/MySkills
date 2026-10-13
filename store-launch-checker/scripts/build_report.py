"""Validate evidence-based checks; render a scoped verdict without a health score."""
import argparse
import json
from pathlib import Path
from datetime import datetime

STATUSES = {'pass', 'fail', 'unknown', 'not_tested', 'not_applicable'}
SEVERITIES = {'critical', 'high', 'medium', 'low', 'info'}


def assess(report):
    for field in ('site_url', 'checked_at', 'environment', 'limitations', 'planned_checks', 'checks'):
        if field not in report:
            raise ValueError(f'Missing {field}')
    if report['environment'] not in {'production', 'staging', 'unknown'}:
        raise ValueError('Environment must be production/staging/unknown')
    if datetime.fromisoformat(report['checked_at'].replace('Z', '+00:00')).utcoffset() is None:
        raise ValueError('checked_at must include timezone')
    if not isinstance(report['limitations'], list) or not all(isinstance(x, str) for x in report['limitations']):
        raise ValueError('limitations must be a string array')
    if not isinstance(report['planned_checks'], list) or not report['planned_checks']:
        raise ValueError('A nonempty check plan is required')
    planned = {}
    for item in report['planned_checks']:
        if not isinstance(item.get('launch_gate'), bool) or not item.get('id') or not item.get('title'):
            raise ValueError('Each planned check needs id, title and boolean launch_gate')
        if item['id'] in planned:
            raise ValueError('Duplicate planned id')
        planned[item['id']] = item
    checks = {}
    for item in report['checks']:
        if item.get('id') not in planned or item['id'] in checks:
            raise ValueError('Unknown or duplicate result id')
        if item.get('status') not in STATUSES or item.get('severity') not in SEVERITIES:
            raise ValueError('Invalid status or severity')
        if item['status'] in {'pass', 'fail'} and not item.get('evidence'):
            raise ValueError('Pass/fail requires evidence')
        if item['status'] in {'pass', 'fail'}:
            if not isinstance(item['evidence'], list) or any(
                not isinstance(e, dict) or not e.get('method') or not e.get('observation')
                or not (e.get('url') or e.get('artifact_path') or e.get('record_reference'))
                for e in item['evidence']
            ):
                raise ValueError('Evidence requires method, observation and URL/artifact/record reference')
        if item['status'] == 'not_applicable' and not item.get('reason'):
            raise ValueError('Not applicable requires a reason')
        checks[item['id']] = {**item, 'title': planned[item['id']]['title'],
                              'launch_gate': planned[item['id']]['launch_gate']}
    for key, item in planned.items():
        if key not in checks:
            checks[key] = {**item, 'status': 'not_tested', 'severity': 'info', 'evidence': [],
                           'reason': 'No result supplied for planned check'}
    rows = list(checks.values())
    applicable = [c for c in rows if c['status'] != 'not_applicable']
    if not applicable or not any(c['launch_gate'] for c in applicable):
        verdict = 'verification_required'
    elif any(c['status'] == 'fail' and (c['launch_gate'] or c['severity'] == 'critical') for c in rows):
        verdict = 'blocked'
    elif report['environment'] == 'unknown' or any(c['launch_gate'] and c['status'] in {'unknown', 'not_tested'} for c in rows):
        verdict = 'verification_required'
    elif any(c['status'] in {'fail', 'unknown', 'not_tested'} for c in applicable):
        verdict = 'ready_with_issues'
    else:
        verdict = 'ready_in_scope'
    return {**report, 'checks': rows, 'verdict': verdict,
            'coverage': {'determinate': sum(c['status'] in {'pass', 'fail'} for c in applicable),
                         'applicable': len(applicable)}}


def render(report):
    lines = ['# 独立站检查报告', '', f'网站：{report["site_url"]}',
             f'检查时间：{report["checked_at"]}', f'环境：{report["environment"]}',
             f'结论：**{report["verdict"]}**（仅限已列范围）',
             f'确定结果覆盖：{report["coverage"]["determinate"]}/{report["coverage"]["applicable"]}，不是健康评分。', '']
    order = {'fail': 0, 'unknown': 1, 'not_tested': 2, 'pass': 3, 'not_applicable': 4}
    for item in sorted(report['checks'], key=lambda c: (not c['launch_gate'], order[c['status']], c['id'])):
        lines += [f'## {item["id"]} · {item["title"]}', '',
                  f'状态：{item["status"]}；级别：{item["severity"]}；上线门槛：{item["launch_gate"]}。', '']
        for key, label in [('reason', '说明'), ('impact', '影响'), ('remediation', '修复'), ('retest', '复测')]:
            if item.get(key):
                lines += [f'{label}：{item[key]}', '']
        for evidence in item.get('evidence', []):
            lines += [f'证据：{json.dumps(evidence, ensure_ascii=False)}', '']
    lines += ['## 范围限制', ''] + [f'- {value}' for value in report['limitations']]
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output-dir', required=True)
    options = parser.parse_args()
    try:
        report = assess(json.loads(Path(options.input).read_text(encoding='utf-8-sig')))
        target = Path(options.output_dir)
        target.mkdir(parents=True, exist_ok=True)
        (target / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (target / 'report.md').write_text(render(report), encoding='utf-8')
        print(f'{report["verdict"]}: {target.resolve()}')
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.exit(1, f'Report rejected: {error}\n')
