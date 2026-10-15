"""Load isolated upstream modules and replace only their browser transport."""
import importlib.util
import os
import random
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

from bitbrowser import CDP

# Upstream imports Browser Harness even when its daemon is not used.
# Keep import-time runtime directories inside this scaffold rather than user config.
os.environ.setdefault('BH_HOME', str(Path(__file__).resolve().parents[1] / 'runtime' / 'browser-harness'))


def pacing_enabled():
    return os.environ.get('BITBROWSER_PACING', 'human').strip().lower() != 'off'


def pause(low, high):
    if pacing_enabled():
        time.sleep(random.uniform(low, high))


PAGE_KEY = '(() => window.__jevFast ? window.__jevFast.pageKey() : null)()'

# Pick a viewport point whose wheel events reach the document: avoid media/embeds and inner scrollers.
SCROLL_POINT = '''(() => {
  for (let i = 0; i < 24; i++) {
    const x = innerWidth * (0.2 + Math.random() * 0.6), y = innerHeight * (0.25 + Math.random() * 0.55);
    const e = document.elementFromPoint(x, y);
    if (!e || e.closest('video,iframe,canvas,embed,object,[role="slider"],[role="dialog"]')) continue;
    let p = e, inner = false;
    while (p && p !== document.body && p !== document.documentElement) {
      const s = getComputedStyle(p);
      if (/(auto|scroll)/.test(s.overflowY) && p.scrollHeight > p.clientHeight + 2) { inner = true; break; }
      p = p.parentElement;
    }
    if (!inner) return [x, y];
  }
  return [innerWidth / 2, innerHeight / 2];
})()'''


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
                # BitBrowser may ignore input sent to a background/hidden target.
                # Activate only the test/task tab, never change the profile fingerprint.
                connection('Target.activateTarget', targetId=self.target)
                self.call('Page.bringToFront')
                self._keep_rendering()
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

        mouse = None

        def _keep_rendering(self):
            # Lazy feeds stall when the window is minimized or the page thinks it lost focus.
            for method, params in (('Emulation.setFocusEmulationEnabled', {'enabled': True}),
                                   ('Page.setWebLifecycleState', {'state': 'active'})):
                try:
                    self.call(method, **params)
                except Exception:
                    pass
            try:
                window = connection('Browser.getWindowForTarget', targetId=self.target)
                if window.get('bounds', {}).get('windowState') == 'minimized':
                    connection('Browser.setWindowBounds', windowId=window['windowId'], bounds={'windowState': 'normal'})
            except Exception:
                pass

        def fresh(self, page, action=None):
            # Live text (video timers, presence) changes the full marker constantly; only content-bound
            # actions compare the target element, others compare document identity, URL, scroll and forms.
            kind = action['kind'] if action else None
            if kind in {'click', 'select'}:
                return super().fresh(page, action)
            if kind == 'fill':
                return super().fresh(page, dict(action, kind='click'))
            if not page.get('page_key'):
                return super().fresh(page, action)
            return self.evaluate(PAGE_KEY) == page['page_key']

        def act(self, action, page, text=None):
            connection('Target.activateTarget', targetId=self.target)
            self.call('Page.bringToFront')
            kind = action['kind']
            if kind == 'scroll':
                pause(0.6, 1.8)
                return self._smooth_scroll(action, page)
            if not pacing_enabled() or kind == 'wait':
                return super().act(action, page, text=text)
            pause(0.6, 1.8)
            rect = action.get('rect')
            if rect and rect.get('w') and rect.get('h') and self.fresh(page, action):
                self._move_to(rect['x'] + rect['w'] * random.uniform(0.3, 0.7),
                              rect['y'] + rect['h'] * random.uniform(0.3, 0.7))
                pause(0.1, 0.35)
            if kind != 'fill' or not text:
                return super().act(action, page, text=text)
            result = super().act(action, page, text='')
            for event in ('keyDown', 'keyUp'):
                self.call('Input.dispatchKeyEvent', type=event, key='Backspace', code='Backspace',
                          windowsVirtualKeyCode=8)
            pause(0.2, 0.5)
            for char in text:
                self.call('Input.insertText', text=char)
                time.sleep(random.uniform(0.05, 0.17) + (random.uniform(0.25, 0.7) if random.random() < 0.06 else 0))
            return result

        def _move_to(self, x, y):
            start = self.mouse or (max(x + random.uniform(-260, 260), 1), max(y + random.uniform(-180, 180), 1))
            steps = random.randint(10, 18)
            bend = random.uniform(-40, 40)
            for index in range(1, steps + 1):
                t = index / steps
                ease = t * t * (3 - 2 * t)
                px = start[0] + (x - start[0]) * ease + bend * (1 - t) * t + random.uniform(-1.5, 1.5)
                py = start[1] + (y - start[1]) * ease + random.uniform(-1.5, 1.5)
                self.call('Input.dispatchMouseEvent', type='mouseMoved', x=max(px, 0), y=max(py, 0))
                time.sleep(random.uniform(0.008, 0.028))
            self.mouse = (x, y)

        def _smooth_scroll(self, action, page):
            if not self.fresh(page, action):
                raise upstream.StalePage('Page changed since this decision. Observe again.')
            x, y = self.evaluate(SCROLL_POINT) or [550, 400]
            if pacing_enabled():
                self._move_to(x, y)
                pause(0.1, 0.3)
            before = self.evaluate('scrollY')
            remaining, sign = abs(action['delta']), 1 if action['delta'] > 0 else -1
            while remaining > 0:
                step = min(remaining, random.randint(60, 140))
                self.call('Input.dispatchMouseEvent', type='mouseWheel', x=x, y=y, deltaX=0, deltaY=sign * step)
                remaining -= step
                pause(0.03, 0.11)
            time.sleep(0.3)
            after = self.evaluate('scrollY')
            fallback = isinstance(before, (int, float)) and isinstance(after, (int, float)) and abs(after - before) < 5
            if fallback:
                self.evaluate(f'window.scrollBy({{top: {int(action["delta"])}, behavior: "smooth"}})')
                time.sleep(0.5)
            self.after_input = action
            pause(0.8, 2.2)
            return {'executed': action['id'], 'script_scroll_fallback': fallback}

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
            try:
                agent.command('tick')
            except ValueError as error:
                if 'TEXT_MODEL_API_KEY' in str(error):
                    return {'status': 'blocked', 'reason': 'text_model_configuration_required',
                            'missing_credentials': ['TEXT_MODEL_API_KEY'], **summary(agent)}
                raise
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
