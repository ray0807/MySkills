"""Load isolated upstream modules and replace only their browser transport."""
import importlib.util
import os
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

from bitbrowser import CDP

# Upstream imports Browser Harness even when its daemon is not used.
# Keep import-time runtime directories inside this scaffold rather than user config.
os.environ.setdefault('BH_HOME', str(Path(__file__).resolve().parents[1] / 'runtime' / 'browser-harness'))


def load_isolated(package, filename):
    name = f'jev_ultrafast._bit_{filename}_{uuid.uuid4().hex}'
    spec = importlib.util.spec_from_file_location(name, Path(package.__file__).parent / f'{filename}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def browser_class(upstream, connection):
    # Each loaded module has its own cdp global; never patch the installed package.
    upstream.cdp = connection

    class FingerprintBrowser(upstream.Browser):
        def __init__(self, url):
            self.target = None
            try:
                self.target = connection('Target.createTarget', url='about:blank', background=True)['targetId']
                self.session = connection('Target.attachToTarget', targetId=self.target, flatten=True)['sessionId']
                # Preserve BitBrowser fingerprint/viewport; no metrics, UA or proxy overrides.
                self.call('Page.navigate', url=url)
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if self.evaluate('document.readyState') == 'complete':
                        break
                    time.sleep(0.05)
            except Exception:
                self.close()
                raise

        def close(self):
            if self.target:
                target, self.target = self.target, None
                connection('Target.closeTarget', targetId=target)

    return FingerprintBrowser


def summary(agent):
    state = agent.snapshot()
    page = state.get('page', {})
    return {
        'jev_status': state['status'], 'verification': 'required',
        'url': page.get('url'), 'title': page.get('title'), 'text': page.get('text', '')[:12000],
        'actions': [{k: h.get(k) for k in ('step', 'kind', 'action', 'url')} for h in state['history']],
        'elapsed_ms': state['elapsed_ms'],
    }


def execute(api, profile_id, url, goal, max_steps, timeout_seconds, cancelled, progress):
    if urlparse(url).scheme not in {'http', 'https'} or not urlparse(url).hostname:
        raise ValueError('Start URL must be HTTP(S)')
    import jev_ultrafast
    browser = load_isolated(jev_ultrafast, 'browser')
    agent_module = load_isolated(jev_ultrafast, 'agent')
    # Agent catches this exception class; both modules must share it.
    agent_module.StalePage = browser.StalePage
    connection = CDP(api.open(profile_id))
    agent = None
    try:
        agent_module.Browser = browser_class(browser, connection)
        agent = agent_module.Agent(url, goal, screenshots=False)
        deadline = time.monotonic() + timeout_seconds
        for step in range(max_steps):
            if cancelled.is_set():
                return {'status': 'cancelled', **summary(agent)}
            if time.monotonic() >= deadline:
                return {'status': 'budget_exceeded', **summary(agent)}
            agent.command('tick')
            result = summary(agent)
            progress({'steps': step + 1, 'url': result['url'], 'jev_status': result['jev_status']})
            if agent.state['status'] in {'done', 'blocked'}:
                return {'status': agent.state['status'], **result}
        return {'status': 'budget_exceeded', **summary(agent)}
    finally:
        try:
            if agent:
                agent.close()
        finally:
            connection.close()
