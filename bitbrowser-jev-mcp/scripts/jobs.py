"""Single-worker jobs; status reads never wait for browser/model execution."""
import copy
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlparse


class Jobs:
    def __init__(self, runner, allowed_profiles):
        self.runner = runner
        self.allowed = frozenset(allowed_profiles)
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.lock = threading.Lock()
        self.records = {}
        self.events = {}

    def submit(self, profile_id, url, goal, max_steps=30, timeout_seconds=180):
        if profile_id not in self.allowed:
            raise ValueError('Profile not allowed')
        if not isinstance(goal, str) or not goal.strip() or len(goal) > 12000:
            raise ValueError('Goal must contain 1–12000 characters')
        parsed = urlparse(url)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username:
            raise ValueError('Invalid start URL')
        if type(max_steps) is not int or not 1 <= max_steps <= 100:
            raise ValueError('max_steps must be 1–100')
        if type(timeout_seconds) is not int or not 10 <= timeout_seconds <= 600:
            raise ValueError('timeout_seconds must be 10–600')
        with self.lock:
            if any(r['status'] in {'queued', 'running', 'cancelling'} for r in self.records.values()):
                raise ValueError('An active job exists; wait or cancel before submitting')
            job_id = uuid.uuid4().hex
            self.events[job_id] = threading.Event()
            self.records[job_id] = {'job_id': job_id, 'profile_id': profile_id, 'status': 'queued',
                                    'created_at': datetime.now(timezone.utc).isoformat()}
        self.pool.submit(self._run, job_id, profile_id, url, goal, max_steps, timeout_seconds)
        return {'job_id': job_id, 'status': 'queued'}

    def _set(self, job_id, values):
        with self.lock:
            self.records[job_id].update(values)

    def _run(self, job_id, profile_id, url, goal, max_steps, timeout_seconds):
        if self.events[job_id].is_set():
            self._set(job_id, {'status': 'cancelled'})
            return
        self._set(job_id, {'status': 'running'})
        try:
            result = self.runner(profile_id, url, goal, max_steps, timeout_seconds,
                                 self.events[job_id], lambda value: self._set(job_id, {'progress': value}))
            self._set(job_id, result)
        except Exception as error:
            # A connection/observation failure can follow a mutation; do not auto retry.
            self._set(job_id, {'status': 'error', 'error_type': type(error).__name__,
                              'message': 'Execution failed. Check server stderr/configuration; verify remote outcome before retry.',
                              'verification': 'required'})
            import logging
            logging.getLogger(__name__).exception('Job %s failed', job_id)

    def get(self, job_id):
        with self.lock:
            if job_id not in self.records:
                raise ValueError('Unknown job; restart loses in-memory state, not remote effects')
            return copy.deepcopy(self.records[job_id])

    def active(self):
        with self.lock:
            return any(r['status'] in {'queued', 'running', 'cancelling'} for r in self.records.values())

    def cancel(self, job_id):
        with self.lock:
            if job_id not in self.records:
                raise ValueError('Unknown job')
            if self.records[job_id]['status'] in {'queued', 'running', 'cancelling'}:
                self.events[job_id].set()
                self.records[job_id]['status'] = 'cancelling'
            return copy.deepcopy(self.records[job_id])
