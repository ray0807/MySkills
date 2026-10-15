"""Persistent observed-element execution for an external planning agent."""
import base64
import threading
import uuid
from urllib.parse import urlparse
from datetime import datetime, timezone

from bitbrowser import CDP
from jev_bridge import browser_class, load_isolated


class RejectedAction(ValueError):
    """No input was sent because the requested action was not observed."""


def web_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username:
        raise ValueError('URL must be HTTP(S), without embedded credentials')
    return url


class Sessions:
    def __init__(self, api, factory=None):
        self.api = api
        self.factory = factory or self._factory
        self.records = {}
        self.lock = threading.RLock()

    @staticmethod
    def _factory(api, profile_id, url):
        import jev_ultrafast
        upstream = load_isolated(jev_ultrafast, 'browser')
        connection = CDP(api.open(profile_id))
        try:
            browser = browser_class(upstream, connection)(url)
            return browser, connection, upstream.StalePage
        except Exception:
            connection.close()
            raise

    def has_open(self):
        with self.lock:
            return bool(self.records)

    def open(self, profile_id, url):
        web_url(url)
        if profile_id not in self.api.allowed:
            raise ValueError('Profile not allowed')
        with self.lock:
            if self.records:
                raise ValueError('Close the active manual session before opening another')
            browser, connection, stale_class = self.factory(self.api, profile_id, url)
            session_id = uuid.uuid4().hex
            self.records[session_id] = {'browser': browser, 'connection': connection, 'stale_class': stale_class,
                                        'owned': {browser.target}, 'snapshot': None, 'receipts': {}}
            return {'session_id': session_id, 'target_id': browser.target, 'status': 'open'}

    def _record(self, session_id):
        if session_id not in self.records:
            raise ValueError('Unknown session; restart loses state, not previously executed actions')
        return self.records[session_id]

    def observe(self, session_id):
        with self.lock:
            record = self._record(session_id)
            page = record['browser'].observe(screenshot=False)
            snapshot_id = uuid.uuid4().hex
            record['snapshot'] = (snapshot_id, page)
            return {'session_id': session_id, 'snapshot_id': snapshot_id,
                    'target_id': record['browser'].target,
                    **{k: page.get(k) for k in ('url', 'title', 'text', 'actions', 'scroll', 'omitted_actions')},
                    'limits': ['visible top-level DOM only', 'iframe/shadow DOM not supported']}

    def read_page(self, session_id, max_scrolls=30, max_chars=60000):
        """Scroll downward and return deduplicated visible text; only scroll inputs are sent."""
        if not 0 <= max_scrolls <= 100 or not 1000 <= max_chars <= 200000:
            raise ValueError('max_scrolls must be 0–100 and max_chars 1000–200000')
        with self.lock:
            record = self._record(session_id)
            browser = record['browser']
            lines, seen, positions = [], set(), []
            page, end_reached, size, scrolls, stale = None, False, 0, 0, 0
            for step in range(max_scrolls + 1):
                page = browser.observe(screenshot=False)
                for line in (page.get('text') or '').splitlines():
                    if line.strip() and line not in seen:
                        seen.add(line)
                        lines.append(line)
                        size += len(line) + 1
                position = (page.get('scroll') or {}).get('y')
                if size >= max_chars:
                    break
                if position is not None and position in positions:
                    end_reached = True
                    break
                positions.append(position)
                down = next((a for a in page['actions'] if a['kind'] == 'scroll' and a.get('delta', 0) > 0), None)
                if not down:
                    end_reached = True
                    break
                if step == max_scrolls:
                    break
                try:
                    browser.act(down, page)
                    scrolls += 1
                    stale = 0
                except record['stale_class']:
                    positions.pop()
                    stale += 1
                    if stale > 5:
                        break
            record['snapshot'] = None
            text = '\n'.join(lines)
            return {'session_id': session_id, 'url': page.get('url'), 'title': page.get('title'),
                    'text': text[:max_chars], 'truncated': size >= max_chars,
                    'scrolls': scrolls, 'end_reached': end_reached,
                    'next_step': 'observe before any further action',
                    'limits': ['visible top-level DOM only', 'iframe/shadow DOM not supported',
                               'lazy content may need wait/observe']}

    def _mutation(self, session_id, snapshot_id, request_id, signature, perform):
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
            raise ValueError('Supply a stable request_id (1–128 characters) for every mutation')
        record = self._record(session_id)
        receipt = record['receipts'].get(request_id)
        if receipt:
            if receipt['signature'] != signature:
                raise ValueError('request_id already used for different parameters')
            return dict(receipt['result'], replay=True)
        snapshot = record['snapshot']
        if not snapshot or snapshot[0] != snapshot_id:
            raise ValueError('Observe first; snapshot is missing, stale or already consumed')
        page = snapshot[1]
        # Consume before any possible mutation. Never auto replay a failed action.
        record['snapshot'] = None
        result = {'status': 'outcome_unknown', 'request_id': request_id, 'verification': 'required',
                  'recorded_at': datetime.now(timezone.utc).isoformat()}
        record['receipts'][request_id] = {'signature': signature, 'result': result}
        try:
            perform(record, page)
            result.update(status='executed', next_step='observe and verify the outcome')
        except RejectedAction:
            result.update(status='rejected', next_step='observe and use an action from the returned list')
        except record['stale_class']:
            # Conservatively report uncertainty: observation can fail after an input.
            result.update(status='stale_or_unknown', next_step='observe; inspect outcome before another action')
        except Exception as error:
            result.update(error_type=type(error).__name__, next_step='observe or reconnect; do not blindly repeat')
        return dict(result)

    def act(self, session_id, snapshot_id, action_id, kind, request_id, text=None):
        if kind not in {'click', 'fill', 'select', 'scroll', 'wait'}:
            raise ValueError('Unsupported action kind')
        if kind == 'fill' and (not isinstance(text, str) or len(text) > 20000):
            raise ValueError('Fill text must be a string of at most 20000 characters')
        with self.lock:
            def perform(record, page):
                action = next((a for a in page['actions'] if a['id'] == action_id), None)
                if not action or action['kind'] != kind:
                    raise RejectedAction('Action must match an observed compatible element')
                record['browser'].act(action, page, text=text)
            return self._mutation(session_id, snapshot_id, request_id,
                                  ('act', snapshot_id, action_id, kind, text), perform)

    def navigate(self, session_id, snapshot_id, url, request_id):
        web_url(url)
        with self.lock:
            def perform(record, page):
                if not record['browser'].fresh(page):
                    raise record['stale_class']('Page changed')
                response = record['browser'].call('Page.navigate', url=url)
                if response.get('errorText'):
                    raise RuntimeError('Navigation failed')
            return self._mutation(session_id, snapshot_id, request_id, ('navigate', snapshot_id, url), perform)

    def press_key(self, session_id, snapshot_id, key, request_id):
        keys = {'Enter': 13, 'Tab': 9, 'Escape': 27, 'Backspace': 8,
                'ArrowDown': 40, 'ArrowUp': 38, 'ArrowLeft': 37, 'ArrowRight': 39}
        if key not in keys:
            raise ValueError('Unsupported key; use a named key from the tool description')
        with self.lock:
            def perform(record, page):
                if not record['browser'].fresh(page):
                    raise record['stale_class']('Page changed')
                for event in ('keyDown', 'keyUp'):
                    record['browser'].call('Input.dispatchKeyEvent', type=event, key=key, code=key,
                                           windowsVirtualKeyCode=keys[key])
            return self._mutation(session_id, snapshot_id, request_id, ('key', snapshot_id, key), perform)

    def history(self, session_id, snapshot_id, direction, request_id):
        if direction not in {'back', 'forward'}:
            raise ValueError('Direction must be back or forward')
        with self.lock:
            def perform(record, page):
                browser = record['browser']
                if not browser.fresh(page):
                    raise record['stale_class']('Page changed')
                history = browser.call('Page.getNavigationHistory')
                index = history['currentIndex'] + (-1 if direction == 'back' else 1)
                if not 0 <= index < len(history['entries']):
                    raise RejectedAction('No navigation entry in that direction')
                browser.call('Page.navigateToHistoryEntry', entryId=history['entries'][index]['id'])
            return self._mutation(session_id, snapshot_id, request_id, ('history', snapshot_id, direction), perform)

    def new_tab(self, session_id, snapshot_id, url, request_id):
        web_url(url)
        with self.lock:
            def perform(record, page):
                if not record['browser'].fresh(page):
                    raise record['stale_class']('Page changed')
                target = record['connection']('Target.createTarget', url=url, background=True)['targetId']
                record['owned'].add(target)
                self.switch_tab(session_id, target)
            return self._mutation(session_id, snapshot_id, request_id, ('new_tab', snapshot_id, url), perform)

    def tabs(self, session_id):
        with self.lock:
            record = self._record(session_id)
            return {'tabs': [{'target_id': t['targetId'], 'title': t.get('title'), 'url': t.get('url'),
                              'owned': t['targetId'] in record['owned'],
                              'current': t['targetId'] == record['browser'].target}
                             for t in record['connection']('Target.getTargets')['targetInfos']
                             if t['type'] == 'page']}

    def switch_tab(self, session_id, target_id):
        with self.lock:
            record = self._record(session_id)
            targets = record['connection']('Target.getTargets')['targetInfos']
            if not any(t['targetId'] == target_id and t['type'] == 'page' for t in targets):
                raise ValueError('Target must be a current page in this profile')
            browser = record['browser']
            response = record['connection']('Target.attachToTarget', targetId=target_id, flatten=True)
            previous = browser.session
            browser.target, browser.session = target_id, response['sessionId']
            browser.after_input = None
            record['snapshot'] = None
            try:
                record['connection']('Target.detachFromTarget', sessionId=previous)
            except Exception:
                pass
            return {'target_id': target_id, 'next_step': 'observe'}

    def screenshot(self, session_id):
        with self.lock:
            return base64.b64decode(self._record(session_id)['browser'].call(
                'Page.captureScreenshot', format='png')['data'])

    def close(self, session_id):
        with self.lock:
            record = self.records.pop(session_id, None)
            if not record:
                return {'status': 'already_closed'}
            failures = []
            try:
                for target in record['owned']:
                    try:
                        record['connection']('Target.closeTarget', targetId=target)
                    except Exception:
                        failures.append(target)
            finally:
                record['connection'].close()
            return {'status': 'closed', 'unconfirmed_tab_cleanup': failures,
                    'profile_closed': False}
