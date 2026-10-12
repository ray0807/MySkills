"""MCP tools for agent-planned goals executed by Jev in BitBrowser."""
import argparse
import importlib.util
import os
import sys
import threading
from pathlib import Path

from bitbrowser import BitBrowser
from jobs import Jobs

root = Path(__file__).resolve().parents[1]
vendor = root / 'vendor' / 'jev-ultrafast'
if vendor.is_dir():
    sys.path.insert(0, str(vendor))


def environment():
    modules = {name: importlib.util.find_spec(name) is not None
               for name in ('jev_ultrafast', 'websocket', 'mcp', 'browser_harness', 'httpx')}
    keys = {name: bool(os.environ.get(name)) for name in ('TYPESAFE_API_KEY', 'TEXT_MODEL_API_KEY')}
    allowed = [p.strip() for p in os.environ.get('BITBROWSER_ALLOWED_PROFILES', '').split(',') if p.strip()]
    step_ready = all(modules.values()) and bool(allowed) and bool(sys.flags.utf8_mode)
    return {'modules': modules, 'credentials_present': keys, 'allowed_profiles': allowed,
            'utf8_mode': bool(sys.flags.utf8_mode),
            'ready': step_ready and all(keys.values()), 'step_ready': step_ready,
            'goal_ready': step_ready and all(keys.values()),
            'limits': ['no iframe/upload/popup guarantee', 'no forced read-only sandbox', 'in-memory job state'],
            'bitbrowser_api': os.environ.get('BITBROWSER_API_URL', 'http://127.0.0.1:54345')}


def main():
    from mcp.server.fastmcp import FastMCP, Image
    from jev_bridge import execute
    from sessions import Sessions
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transport', choices=['stdio', 'streamable-http'], default='stdio')
    parser.add_argument('--port', type=int, default=8767)
    args = parser.parse_args()
    allowed = environment()['allowed_profiles']
    api = BitBrowser(os.environ.get('BITBROWSER_API_URL', 'http://127.0.0.1:54345'), allowed)
    jobs = Jobs(lambda *values: execute(api, *values), allowed)
    sessions = Sessions(api)
    coordinator = threading.RLock()
    mcp = FastMCP('bitbrowser-jev', host='127.0.0.1', port=args.port)

    @mcp.tool()
    def environment_check() -> dict:
        """Check dependencies/configuration without opening profiles or calling model APIs."""
        return environment()

    @mcp.tool()
    def list_profiles(page: int = 0, page_size: int = 20) -> dict:
        """List allowed profiles in this API page; excludes cookies/proxies/passwords."""
        return {'profiles': api.list_profiles(page, page_size), 'page': page}

    @mcp.tool()
    def submit_goal(profile_id: str, url: str, goal: str, max_steps: int = 30, timeout_seconds: int = 180) -> dict:
        """Execute one user-authorized natural-language stage; calls paid configured models asynchronously."""
        if not environment()['ready']:
            raise ValueError('Environment incomplete; call environment_check and configure first')
        with coordinator:
            if sessions.has_open():
                raise ValueError('Close manual session before starting Jev goal execution')
            return jobs.submit(profile_id, url, goal, max_steps, timeout_seconds)

    @mcp.tool()
    def open_session(profile_id: str, url: str) -> dict:
        """Open a persistent tab for external AI decisions; no executor model credentials required."""
        if not environment()['step_ready']:
            raise ValueError('Step environment incomplete; call environment_check')
        with coordinator:
            if jobs.active():
                raise ValueError('Wait for or cancel the active Jev job before opening a manual session')
            return sessions.open(profile_id, url)

    @mcp.tool()
    def observe(session_id: str) -> dict:
        """Return visible text and indexed actions with a fresh snapshot_id. No business decisions."""
        return sessions.observe(session_id)

    @mcp.tool()
    def click(session_id: str, snapshot_id: str, action_id: str, request_id: str) -> dict:
        """Click an observed click action. Stable request_id prevents duplicate execution."""
        return sessions.act(session_id, snapshot_id, action_id, 'click', request_id)

    @mcp.tool()
    def fill(session_id: str, snapshot_id: str, action_id: str, text: str, request_id: str) -> dict:
        """Fill an observed editable action with text supplied by the external AI."""
        return sessions.act(session_id, snapshot_id, action_id, 'fill', request_id, text)

    @mcp.tool()
    def select(session_id: str, snapshot_id: str, action_id: str, request_id: str) -> dict:
        """Select an exact observed option action; no guessed values or selectors."""
        return sessions.act(session_id, snapshot_id, action_id, 'select', request_id)

    @mcp.tool()
    def scroll(session_id: str, snapshot_id: str, action_id: str, request_id: str) -> dict:
        """Execute observed scroll_up/scroll_down action; nested scroll regions not supported."""
        return sessions.act(session_id, snapshot_id, action_id, 'scroll', request_id)

    @mcp.tool()
    def wait(session_id: str, snapshot_id: str, request_id: str) -> dict:
        """Execute observed short wait; observe again afterwards rather than guessing readiness."""
        return sessions.act(session_id, snapshot_id, 'wait', 'wait', request_id)

    @mcp.tool()
    def navigate(session_id: str, snapshot_id: str, url: str, request_id: str) -> dict:
        """Navigate the persistent tab to an HTTP(S) URL; invalidates previous observation."""
        return sessions.navigate(session_id, snapshot_id, url, request_id)

    @mcp.tool()
    def press_key(session_id: str, snapshot_id: str, key: str, request_id: str) -> dict:
        """Press Enter/Tab/Escape/Backspace/ArrowDown/ArrowUp/ArrowLeft/ArrowRight on current focus."""
        return sessions.press_key(session_id, snapshot_id, key, request_id)

    @mcp.tool()
    def list_tabs(session_id: str) -> dict:
        """List current page targets, including popups and existing tabs of this profile."""
        return sessions.tabs(session_id)

    @mcp.tool()
    def new_tab(session_id: str, snapshot_id: str, url: str, request_id: str) -> dict:
        """Create and switch to a scaffold-owned tab while retaining other tabs."""
        return sessions.new_tab(session_id, snapshot_id, url, request_id)

    @mcp.tool()
    def browser_history(session_id: str, snapshot_id: str, direction: str, request_id: str) -> dict:
        """Navigate back or forward using actual browser history entries."""
        return sessions.history(session_id, snapshot_id, direction, request_id)

    @mcp.tool()
    def switch_tab(session_id: str, target_id: str) -> dict:
        """Attach to a listed tab; observe again before actions. Existing tabs are not closed on cleanup."""
        return sessions.switch_tab(session_id, target_id)

    @mcp.tool()
    def screenshot(session_id: str) -> Image:
        """Capture current tab as an MCP image for external AI inspection."""
        return Image(data=sessions.screenshot(session_id), format='png')

    @mcp.tool()
    def close_session(session_id: str) -> dict:
        """Close only scaffold-created tabs and disconnect; preserve profile and user tabs."""
        with coordinator:
            return sessions.close(session_id)

    @mcp.tool()
    def get_job(job_id: str) -> dict:
        """Read execution evidence. Jev done requires independent outcome verification."""
        return jobs.get(job_id)

    @mcp.tool()
    def cancel_job(job_id: str) -> dict:
        """Request cooperative cancellation; cannot undo executed actions."""
        return jobs.cancel(job_id)

    try:
        mcp.run(transport=args.transport)
    finally:
        for session_id in list(sessions.records):
            sessions.close(session_id)


if __name__ == '__main__':
    main()
