"""Shared freshness policy. Unknown dates remain unknown; discovery is not publication."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULTS = {'max_post_age_days': 30, 'overlap_hours': 24, 'catchup_days': 7}


def policy(directory):
    path = Path(directory) / 'time-policy.json'
    result = dict(DEFAULTS)
    if path.exists():
        raw = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw, dict):
            raise ValueError('time-policy.json must be an object')
        for key in DEFAULTS:
            value = raw.get(key, result[key])
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f'{key} must be a positive integer')
            result[key] = value
    return result


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None:
        raise ValueError('Timezone required')
    return parsed


def freshness(row, now=None, max_days=30):
    now = now or datetime.now(timezone.utc)
    text = row.get('published_at_iso') or row.get('published_at') or ''
    if not isinstance(text, str) or not text.strip():
        return '日期未知'
    text = text.strip()
    try:
        published = timestamp(text)
        age = (now - published).total_seconds() / 86400
        if age < -1:
            return '日期异常'
        return '超期历史' if age > max_days else '近期（未核验）'
    except ValueError:
        pass
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        try:
            day = datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
            # Date-only evidence has no source timezone; allow a wide boundary interval.
            if now - (day + timedelta(days=2)) > timedelta(days=max_days):
                return '超期历史'
            return '日期待确认'
        except ValueError:
            return '日期异常'
    # Search date labels refer to when that label was observed, not export time.
    observed = row.get('published_observed_at') or row.get('found_at')
    try:
        anchor = timestamp(observed) if observed else None
    except (ValueError, TypeError, AttributeError):
        anchor = None
    match = re.fullmatch(r'(\d+)\s*(minutes?|hours?|days?|weeks?|months?|years?)\s+ago', text, re.I)
    chinese = re.fullmatch(r'(\d+)\s*(分钟|小时|天|周|个月|年)前', text)
    match = match or chinese
    if not match or not anchor:
        return '日期未知'
    amount, unit = int(match[1]), match[2].lower()
    unit = {'分钟': 'minute', '小时': 'hour', '天': 'day', '周': 'week', '个月': 'month', '年': 'year'}.get(unit, unit.rstrip('s'))
    bounds = {'minute': (1/1440, 1/1440), 'hour': (1/24, 1/24), 'day': (1, 1),
              'week': (7, 7), 'month': (28, 31), 'year': (365, 366)}
    low, high = bounds[unit]
    elapsed = (now - anchor).total_seconds() / 86400
    # Display values may be rounded/truncated: retain an interval, not a fake exact date.
    minimum, maximum = max(0, (amount - 1) * low) + elapsed, (amount + 1) * high + elapsed
    if minimum > max_days:
        return '超期历史'
    if maximum <= max_days and minimum >= -1:
        return '近期（搜索显示）'
    return '日期待确认'
