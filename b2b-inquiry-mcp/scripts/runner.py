"""One active role run: opens its BitBrowser profile, guards sends and records them in the ledger."""
import random
import threading


class Runner:
    def __init__(self, config, ledger, sessions):
        self.config = config
        self.ledger = ledger
        self.sessions = sessions
        self.active = None
        self.receipts = {}
        self.gap = config['limits']['min_send_interval_seconds']
        self.lock = threading.RLock()

    def _daily_cap(self, role):
        side = self.config['roles'][role]['side']
        return self.config['limits'][f'{side}_daily_messages']

    def roles(self):
        return {'roles': [{'role': role, 'label': info['label'], 'platform': info['platform'], 'side': info['side'],
                           'configured': bool(info['profile_id']), 'start_url': info['start_url'],
                           'sent_today': self.ledger.sent_today(role), 'daily_cap': self._daily_cap(role)}
                          for role, info in self.config['roles'].items()],
                'active_role': self.active and self.active['role']}

    def start(self, role, goal=''):
        with self.lock:
            if role not in self.config['roles']:
                raise ValueError('role must be one of: ' + ', '.join(self.config['roles']))
            if self.active:
                raise ValueError(f"A run for {self.active['role']} is active; end_run first")
            info = self.config['roles'][role]
            if not info['profile_id']:
                raise ValueError(f'Configure roles.{role}.profile_id in {self.config["path"]}')
            session = self.sessions.open(info['profile_id'], info['start_url'])
            run_id = self.ledger.start_run(role, goal)
            self.active = {'run_id': run_id, 'role': role, 'session_id': session['session_id'], 'goal': goal}
            brief = self.config['buyer_goal'] if info['side'] == 'buyer' else self.config['seller_policy']
            return {'run_id': run_id, 'role': role, 'label': info['label'], 'side': info['side'],
                    'start_url': info['start_url'], 'goal': goal,
                    'buyer_goal' if info['side'] == 'buyer' else 'seller_policy': brief,
                    'limits': self.config['limits'], 'sent_today': self.ledger.sent_today(role),
                    'stats_30d': self.ledger.stats(role, 30)['roles'].get(role),
                    'next_step': 'observe, then work toward the goal; send only through send_message'}

    def session_id(self):
        if not self.active:
            raise ValueError('No active run; call start_run with a role first')
        return self.active['session_id']

    def status(self):
        if not self.active:
            return {'active': False}
        role = self.active['role']
        return {'active': True, **{k: self.active[k] for k in ('run_id', 'role', 'goal')},
                'sent_today': self.ledger.sent_today(role), 'daily_cap': self._daily_cap(role),
                'run_stats': self.ledger.stats(role, 30, self.active['run_id'])['roles'].get(role)}

    def end(self):
        with self.lock:
            if not self.active:
                return {'status': 'no_active_run'}
            active, self.active = self.active, None
            try:
                closed = self.sessions.close(active['session_id'])
            finally:
                self.ledger.end_run(active['run_id'])
            return {'status': 'ended', 'run_id': active['run_id'], 'role': active['role'], 'session': closed,
                    'run_stats': self.ledger.stats(active['role'], 30, active['run_id'])['roles'].get(active['role'])}

    def send(self, snapshot_id, send_action_id, request_id, counterpart, text, product='', url='', kind=''):
        with self.lock:
            session_id = self.session_id()
            role = self.active['role']
            side = self.config['roles'][role]['side']
            kind = kind or ('inquiry' if side == 'buyer' else 'reply')
            if kind not in {'inquiry', 'reply', 'follow_up'}:
                raise ValueError('kind must be inquiry, reply or follow_up')
            if not counterpart.strip() or not text.strip() or len(text) > 4000:
                raise ValueError('counterpart and text (≤4000 characters) are required')
            if request_id in self.receipts:
                previous = self.receipts[request_id]
                return dict(previous, replay=True)
            if self.ledger.sent_today(role) >= self._daily_cap(role):
                return {'status': 'daily_limit_reached', 'daily_cap': self._daily_cap(role),
                        'next_step': 'do not send; end_run or continue reading only'}
            last = self.ledger.last_outbound_at(role)
            if last:
                waited = (self.ledger.now() - last).total_seconds()
                if waited < self.gap:
                    return {'status': 'too_soon', 'retry_after_seconds': int(self.gap - waited) + 1,
                            'next_step': 'read other threads or wait; the message was not sent'}
            if kind == 'inquiry' and self.ledger.recently_inquired(role, counterpart, product,
                                                                    self.config['limits']['recontact_days']):
                return {'status': 'duplicate_inquiry', 'recontact_days': self.config['limits']['recontact_days'],
                        'next_step': 'skip this counterpart or send a follow_up only if the goal requires it'}
            result = self.sessions.act(session_id, snapshot_id, send_action_id, 'click', request_id)
            if result.get('status') == 'rejected':
                return dict(result, recorded=False)
            status = 'sent_unverified' if result.get('status') == 'executed' else 'unknown'
            message_id = self.ledger.add_outbound(self.active['run_id'], role, counterpart, product, url, kind, text,
                                                  status)
            limits = self.config['limits']
            self.gap = random.uniform(limits['min_send_interval_seconds'], limits['max_send_interval_seconds'])
            receipt = dict(result, message_id=message_id, ledger_status=status, recorded=True,
                           next_step='observe the thread; call confirm_sent with whether the message appears')
            self.receipts[request_id] = receipt
            return receipt

    def record_inbound(self, counterpart, text, product='', url='', seen_at_text='', fields=None):
        role = self.active['role'] if self.active else None
        if not role:
            raise ValueError('No active run; call start_run with a role first')
        if not counterpart.strip() or not text.strip():
            raise ValueError('counterpart and text are required')
        allowed = {'price', 'currency', 'moq', 'lead_time', 'sample', 'shipping', 'payment', 'notes'}
        fields = {k: str(v) for k, v in (fields or {}).items() if k in allowed and v not in (None, '')}
        message_id, duplicate = self.ledger.add_inbound(self.active['run_id'], role, counterpart, product, url, text,
                                                        seen_at_text or None, fields or None)
        return {'message_id': message_id, 'duplicate': duplicate}
