"""Create a complete plan; every applicable check starts not_tested."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from public_probe import valid_url


def create_plan(site_url, environment='unknown', site_type='ecommerce'):
    site_url = valid_url(site_url)
    if environment not in {'unknown', 'staging', 'production'} or site_type not in {'ecommerce', 'lead'}:
        raise ValueError('Unsupported environment or site type')
    text = (Path(__file__).resolve().parents[1] / 'references/checklist.md').read_text(encoding='utf-8')
    rows = re.findall(r'^\| ([A-Z]+-\d+) \| ([GROC]) \| (.*?) \|$', text, re.M)
    if not rows:
        raise ValueError('Checklist could not be loaded')
    planned, checks = [], []
    for check_id, tier, description in rows:
        ecommerce_only = check_id.startswith(('CART-', 'PAY-', 'FUL-'))
        gate = tier == 'G' and not (site_type == 'lead' and ecommerce_only)
        planned.append({'id': check_id, 'title': description, 'launch_gate': gate, 'tier': tier})
        status = 'not_applicable' if site_type == 'lead' and ecommerce_only else 'not_tested'
        reason = '询盘型站点以 LEAD 链路替代在线交易' if status == 'not_applicable' else '待执行；不能视为通过'
        checks.append({'id': check_id, 'status': status, 'severity': 'info', 'evidence': [], 'reason': reason})
    if site_type == 'lead':
        for index, title in enumerate(('联系入口', '表单字段和重复提交反馈', '测试询盘到达邮箱/CRM', '隐私与报价流程'), 1):
            check_id = f'LEAD-{index:02d}'
            planned.append({'id': check_id, 'title': title, 'launch_gate': True, 'tier': 'G'})
            checks.append({'id': check_id, 'status': 'not_tested', 'severity': 'info', 'evidence': [],
                           'reason': '待执行；测试提交需明确授权'})
    return {'site_url': site_url, 'checked_at': datetime.now(timezone.utc).isoformat(), 'environment': environment,
            'site_type': site_type, 'markets': [], 'sample_urls': [site_url], 'tools': [],
            'limitations': ['初始计划尚未执行，按实际市场、样本、工具与权限更新'],
            'planned_checks': planned, 'checks': checks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-url', required=True)
    parser.add_argument('--environment', choices=['unknown', 'staging', 'production'], default='unknown')
    parser.add_argument('--site-type', choices=['ecommerce', 'lead'], default='ecommerce')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        plan = create_plan(args.site_url, args.environment, args.site_type)
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Created {len(plan["planned_checks"])} checks; none has been tested.')
    except (ValueError, OSError) as error:
        parser.exit(1, f'Plan failed: {error}\n')
