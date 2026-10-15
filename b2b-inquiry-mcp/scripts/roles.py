"""Role definitions and local configuration for 1688 / Alibaba.com inquiry runs."""
import json
from pathlib import Path

ROLES = {
    '1688_buyer': {'platform': '1688', 'side': 'buyer', 'label': '1688 买方', 'start_url': 'https://www.1688.com/'},
    '1688_seller': {'platform': '1688', 'side': 'seller', 'label': '1688 卖方', 'start_url': 'https://work.1688.com/'},
    'alibaba_buyer': {'platform': 'alibaba', 'side': 'buyer', 'label': '国际站买方',
                      'start_url': 'https://www.alibaba.com/'},
    'alibaba_seller': {'platform': 'alibaba', 'side': 'seller', 'label': '国际站卖方',
                       'start_url': 'https://i.alibaba.com/'},
}

DEFAULT_LIMITS = {
    'buyer_daily_messages': 20,
    'seller_daily_messages': 120,
    'min_send_interval_seconds': 90,
    'max_send_interval_seconds': 240,
    'recontact_days': 14,
}


def load_config(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    limits = dict(DEFAULT_LIMITS, **(data.get('limits') or {}))
    for key, value in limits.items():
        if not isinstance(value, int) or value < 0:
            raise ValueError(f'limits.{key} must be a non-negative integer')
    if limits['min_send_interval_seconds'] > limits['max_send_interval_seconds']:
        raise ValueError('min_send_interval_seconds must not exceed max_send_interval_seconds')
    roles = {}
    for role, base in ROLES.items():
        custom = (data.get('roles') or {}).get(role) or {}
        roles[role] = dict(base, profile_id=(custom.get('profile_id') or '').strip(),
                           start_url=custom.get('start_url') or base['start_url'])
    return {'path': str(path), 'exists': path.exists(), 'roles': roles, 'limits': limits,
            'buyer_goal': data.get('buyer_goal') or {}, 'seller_policy': data.get('seller_policy') or {}}
