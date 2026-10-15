"""MCP for 1688 / Alibaba.com buyer inquiries and seller replies in BitBrowser, with a local statistics ledger."""
import argparse
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BROWSER_SKILL = Path(os.environ.get('BITBROWSER_JEV_MCP_DIR') or ROOT.parent / 'bitbrowser-jev-mcp')
sys.path.append(str(BROWSER_SKILL / 'scripts'))
if (BROWSER_SKILL / 'vendor' / 'jev-ultrafast').is_dir():
    sys.path.append(str(BROWSER_SKILL / 'vendor' / 'jev-ultrafast'))

from roles import load_config  # noqa: E402

CONFIG_PATH = Path(os.environ.get('B2B_INQUIRY_CONFIG') or ROOT / 'config.json')
DATA_DIR = Path(os.environ.get('B2B_INQUIRY_DATA') or ROOT / 'runtime' / 'data')
API_URL = os.environ.get('BITBROWSER_API_URL', 'http://127.0.0.1:54345')


def environment(config=None):
    modules = {name: importlib.util.find_spec(name) is not None
               for name in ('mcp', 'websocket', 'jev_ultrafast', 'sessions')}
    error = None
    try:
        config = config or load_config(CONFIG_PATH)
    except (ValueError, OSError) as exc:
        error = str(exc)
    roles = {role: bool(info['profile_id']) for role, info in config['roles'].items()} if config else {}
    return {'modules': modules, 'browser_skill_dir': str(BROWSER_SKILL),
            'browser_skill_found': (BROWSER_SKILL / 'scripts' / 'sessions.py').is_file(),
            'config_path': str(CONFIG_PATH), 'config_exists': CONFIG_PATH.is_file(), 'config_error': error,
            'roles_configured': roles, 'data_dir': str(DATA_DIR), 'bitbrowser_api': API_URL,
            'utf8_mode': bool(sys.flags.utf8_mode),
            'ready': all(modules.values()) and not error and bool(sys.flags.utf8_mode)}


def main():
    from mcp.server.fastmcp import FastMCP, Image
    from bitbrowser import BitBrowser
    from sessions import Sessions
    from ledger import Ledger
    from runner import Runner

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transport', choices=['stdio', 'streamable-http'], default='stdio')
    parser.add_argument('--port', type=int, default=8768)
    args = parser.parse_args()
    config = load_config(CONFIG_PATH)
    api = BitBrowser(API_URL, [])
    sessions = Sessions(api)
    ledger = Ledger(DATA_DIR / 'ledger.sqlite3')
    runner = Runner(config, ledger, sessions)
    mcp = FastMCP('b2b-inquiry', host='127.0.0.1', port=args.port)

    @mcp.tool()
    def environment_check() -> dict:
        """Check dependencies, the shared browser skill, config and configured role windows."""
        return environment(config)

    @mcp.tool()
    def list_roles() -> dict:
        """List the four roles, whether a window is configured, today's sends and daily caps. Ask the user to choose a role for this run."""
        return runner.roles()

    @mcp.tool()
    def list_profiles(page: int = 0, page_size: int = 20) -> dict:
        """List local BitBrowser IDs/names for user selection; does not authorize opening them."""
        if page < 0 or not 1 <= page_size <= 100:
            raise ValueError('Invalid pagination')
        data = api.request('/browser/list', {'page': page, 'pageSize': page_size})
        rows = data.get('list', []) if isinstance(data, dict) else []
        return {'profiles': [{'id': r['id'], 'name': r.get('name', ''), 'seq': r.get('seq')}
                             for r in rows if r.get('id')], 'page': page,
                'next_step': 'Ask the user to select a profile_id for this run, even if one was used before.'}

    @mcp.tool()
    def start_run(role: str, profile_id: str, goal: str = '') -> dict:
        """Start the role and BitBrowser profile_id explicitly selected by the user for this run: 1688_buyer, 1688_seller, alibaba_buyer or alibaba_seller. Opens its window."""
        return runner.start(role, profile_id, goal)

    @mcp.tool()
    def run_status() -> dict:
        """Active role, today's sends against the cap and statistics for this run."""
        return runner.status()

    @mcp.tool()
    def end_run() -> dict:
        """Close the run's tab (window and login are kept) and return the run statistics."""
        return runner.end()

    @mcp.tool()
    def observe() -> dict:
        """Visible text and actions of the active run's tab with a fresh snapshot_id."""
        return sessions.observe(runner.session_id())

    @mcp.tool()
    def read_page(max_scrolls: int = 30, max_chars: int = 60000) -> dict:
        """Scroll down and return deduplicated page text (message lists, threads, search results)."""
        return sessions.read_page(runner.session_id(), max_scrolls, max_chars)

    @mcp.tool()
    def click(snapshot_id: str, action_id: str, request_id: str) -> dict:
        """Click an observed action. Never use this for the final send button; use send_message."""
        return sessions.act(runner.session_id(), snapshot_id, action_id, 'click', request_id)

    @mcp.tool()
    def fill(snapshot_id: str, action_id: str, text: str, request_id: str) -> dict:
        """Type AI-written text into an observed input (human-paced). Does not send."""
        return sessions.act(runner.session_id(), snapshot_id, action_id, 'fill', request_id, text)

    @mcp.tool()
    def scroll(snapshot_id: str, action_id: str, request_id: str) -> dict:
        """Execute an observed scroll_up/scroll_down action."""
        return sessions.act(runner.session_id(), snapshot_id, action_id, 'scroll', request_id)

    @mcp.tool()
    def wait(snapshot_id: str, request_id: str) -> dict:
        """Short wait, then observe again."""
        return sessions.act(runner.session_id(), snapshot_id, 'wait', 'wait', request_id)

    @mcp.tool()
    def navigate(snapshot_id: str, url: str, request_id: str) -> dict:
        """Navigate the run's tab to an HTTP(S) URL."""
        return sessions.navigate(runner.session_id(), snapshot_id, url, request_id)

    @mcp.tool()
    def press_key(snapshot_id: str, key: str, request_id: str) -> dict:
        """Press Tab/Escape/Backspace/arrow keys. Do not press Enter to send; use send_message."""
        if key == 'Enter':
            raise ValueError('Enter may send a message; click the send button through send_message instead')
        return sessions.press_key(runner.session_id(), snapshot_id, key, request_id)

    @mcp.tool()
    def list_tabs() -> dict:
        """List page targets in the run's window."""
        return sessions.tabs(runner.session_id())

    @mcp.tool()
    def switch_tab(target_id: str) -> dict:
        """Switch to a listed tab (e.g. a chat window opened by the site); observe afterwards."""
        return sessions.switch_tab(runner.session_id(), target_id)

    @mcp.tool()
    def new_tab(snapshot_id: str, url: str, request_id: str) -> dict:
        """Open and switch to a new tab owned by this run."""
        return sessions.new_tab(runner.session_id(), snapshot_id, url, request_id)

    @mcp.tool()
    def browser_history(snapshot_id: str, direction: str, request_id: str) -> dict:
        """Go back or forward in the run's tab."""
        return sessions.history(runner.session_id(), snapshot_id, direction, request_id)

    @mcp.tool()
    def screenshot() -> Image:
        """Screenshot of the run's tab for visual checks."""
        return Image(data=sessions.screenshot(runner.session_id()), format='png')

    @mcp.tool()
    def send_message(snapshot_id: str, send_action_id: str, request_id: str, counterpart: str, text: str,
                     product: str = '', url: str = '', kind: str = '') -> dict:
        """Click the observed send button for text already typed with fill, enforcing daily caps, human send intervals
        and no repeat inquiry to the same counterpart+product; records the message. kind: inquiry/reply/follow_up."""
        return runner.send(snapshot_id, send_action_id, request_id, counterpart, text, product, url, kind)

    @mcp.tool()
    def confirm_sent(message_id: int, delivered: bool) -> dict:
        """After observing the thread, mark a sent message as delivered or failed."""
        ledger.set_status(message_id, 'sent' if delivered else 'failed')
        return {'message_id': message_id, 'status': 'sent' if delivered else 'failed'}

    @mcp.tool()
    def record_inbound(counterpart: str, text: str, product: str = '', url: str = '', seen_at_text: str = '',
                       fields: dict | None = None) -> dict:
        """Record a message received from the counterpart. fields may hold price, currency, moq, lead_time, sample,
        shipping, payment, notes extracted from the message. Duplicates are ignored."""
        return runner.record_inbound(counterpart, text, product, url, seen_at_text, fields)

    @mcp.tool()
    def get_stats(role: str = '', days: int = 30) -> dict:
        """Reply rate, first-reply time, awaiting replies and captured quotes per role."""
        if not 1 <= days <= 365:
            raise ValueError('days must be 1–365')
        return ledger.stats(role or None, days)

    @mcp.tool()
    def export_csv(role: str = '', days: int = 30) -> dict:
        """Export recorded messages to a UTF-8 CSV in the data directory."""
        return ledger.export_csv(DATA_DIR / 'exports', role or None, days)

    try:
        mcp.run(transport=args.transport)
    finally:
        if runner.active:
            runner.end()


if __name__ == '__main__':
    main()
