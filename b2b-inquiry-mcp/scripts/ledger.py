"""Local SQLite ledger of inquiry/reply messages and response statistics."""
import csv
import hashlib
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

SCHEMA = '''
create table if not exists runs(id text primary key, role text not null, goal text, started_at text not null,
  ended_at text);
create table if not exists conversations(id integer primary key, role text not null, counterpart text not null,
  product text not null default '', url text, created_at text not null, unique(role, counterpart, product));
create table if not exists messages(id integer primary key, conversation_id integer not null, run_id text,
  direction text not null, kind text not null, text text not null, digest text not null, status text not null,
  at text not null, seen_at_text text, fields text, unique(conversation_id, direction, digest));
'''
SENT = ('sent_unverified', 'sent', 'unknown')


def utc(moment=None):
    return (moment or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(timespec='seconds')


def parse(value):
    return datetime.fromisoformat(value)


class Ledger:
    def __init__(self, path, now=None):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.lock = threading.Lock()
        self.now = now or (lambda: datetime.now(timezone.utc))

    def start_run(self, role, goal=''):
        run_id = uuid.uuid4().hex
        with self.lock, self.db:
            self.db.execute('insert into runs values (?,?,?,?,null)', (run_id, role, goal, utc(self.now())))
        return run_id

    def end_run(self, run_id):
        with self.lock, self.db:
            self.db.execute('update runs set ended_at=? where id=?', (utc(self.now()), run_id))

    def _conversation(self, role, counterpart, product, url):
        self.db.execute('insert or ignore into conversations(role,counterpart,product,url,created_at) values (?,?,?,?,?)',
                        (role, counterpart, product, url or None, utc(self.now())))
        if url:
            self.db.execute('update conversations set url=? where role=? and counterpart=? and product=?',
                            (url, role, counterpart, product))
        return self.db.execute('select id from conversations where role=? and counterpart=? and product=?',
                               (role, counterpart, product)).fetchone()['id']

    def _add(self, run_id, role, counterpart, product, url, direction, kind, text, status, seen_at_text=None,
             fields=None):
        digest = hashlib.sha256(text.strip().encode()).hexdigest()
        with self.lock, self.db:
            conversation = self._conversation(role, counterpart.strip(), (product or '').strip(), url)
            cursor = self.db.execute(
                'insert or ignore into messages(conversation_id,run_id,direction,kind,text,digest,status,at,'
                'seen_at_text,fields) values (?,?,?,?,?,?,?,?,?,?)',
                (conversation, run_id, direction, kind, text, digest, status, utc(self.now()), seen_at_text,
                 json.dumps(fields, ensure_ascii=False) if fields else None))
            if cursor.rowcount:
                return cursor.lastrowid, False
            row = self.db.execute('select id from messages where conversation_id=? and direction=? and digest=?',
                                  (conversation, direction, digest)).fetchone()
            return row['id'], True

    def add_outbound(self, run_id, role, counterpart, product, url, kind, text, status):
        return self._add(run_id, role, counterpart, product, url, 'out', kind, text, status)[0]

    def add_inbound(self, run_id, role, counterpart, product, url, text, seen_at_text=None, fields=None):
        return self._add(run_id, role, counterpart, product, url, 'in', 'inbound', text, 'received',
                         seen_at_text, fields)

    def set_status(self, message_id, status):
        with self.lock, self.db:
            changed = self.db.execute("update messages set status=? where id=? and direction='out'",
                                      (status, message_id)).rowcount
        if not changed:
            raise ValueError('Unknown outbound message_id')

    def sent_since(self, role, since):
        row = self.db.execute(
            "select count(*) n from messages m join conversations c on c.id=m.conversation_id "
            f"where c.role=? and m.direction='out' and m.status in {SENT} and m.at>=?", (role, utc(since))).fetchone()
        return row['n']

    def sent_today(self, role):
        local = self.now().astimezone()
        return self.sent_since(role, local.replace(hour=0, minute=0, second=0, microsecond=0))

    def last_outbound_at(self, role):
        row = self.db.execute(
            "select max(m.at) at from messages m join conversations c on c.id=m.conversation_id "
            f"where c.role=? and m.direction='out' and m.status in {SENT}", (role,)).fetchone()
        return parse(row['at']) if row['at'] else None

    def recently_inquired(self, role, counterpart, product, days):
        row = self.db.execute(
            "select max(m.at) at from messages m join conversations c on c.id=m.conversation_id "
            f"where c.role=? and c.counterpart=? and c.product=? and m.direction='out' and m.kind='inquiry' "
            f"and m.status in {SENT}", (role, counterpart.strip(), (product or '').strip())).fetchone()
        return bool(row['at']) and parse(row['at']) >= self.now() - timedelta(days=days)

    def _rows(self, role, days, run_id=None):
        query = ('select c.id cid, c.role, c.counterpart, c.product, c.url, m.id, m.direction, m.kind, m.text, '
                 'm.status, m.at, m.seen_at_text, m.fields, m.run_id from messages m '
                 'join conversations c on c.id=m.conversation_id where m.at>=?')
        values = [utc(self.now() - timedelta(days=days))]
        if role:
            query += ' and c.role=?'
            values.append(role)
        if run_id:
            query += ' and m.run_id=?'
            values.append(run_id)
        return [dict(r) for r in self.db.execute(query + ' order by m.at, m.id', values)]

    def stats(self, role=None, days=30, run_id=None):
        rows = self._rows(role, days, run_id)
        result = {}
        for current in sorted({r['role'] for r in rows}):
            threads = {}
            for row in (r for r in rows if r['role'] == current):
                threads.setdefault(row['cid'], []).append(row)
            outbound = [r for r in rows if r['role'] == current and r['direction'] == 'out' and r['status'] in SENT]
            inbound = [r for r in rows if r['role'] == current and r['direction'] == 'in']
            contacted, replied, waits, awaiting, unanswered, quotes = 0, 0, [], 0, 0, []
            for messages in threads.values():
                first_out = next((m for m in messages if m['direction'] == 'out' and m['status'] in SENT), None)
                if first_out:
                    contacted += 1
                    reply = next((m for m in messages if m['direction'] == 'in' and m['at'] >= first_out['at']), None)
                    if reply:
                        replied += 1
                        waits.append((parse(reply['at']) - parse(first_out['at'])).total_seconds() / 60)
                last = messages[-1]
                if last['direction'] == 'out' and last['status'] in SENT:
                    awaiting += 1
                if last['direction'] == 'in':
                    unanswered += 1
                for m in messages:
                    if m['direction'] == 'in' and m['fields']:
                        quotes.append({'counterpart': m['counterpart'], 'product': m['product'], 'at': m['at'],
                                       **json.loads(m['fields'])})
            result[current] = {
                'conversations': len(threads), 'messages_sent': len(outbound), 'messages_received': len(inbound),
                'inquiries_sent': len([m for m in outbound if m['kind'] == 'inquiry']),
                'unverified_sends': len([m for m in outbound if m['status'] != 'sent']),
                'counterparts_contacted': contacted, 'counterparts_replied': replied,
                'reply_rate': round(replied / contacted, 3) if contacted else None,
                'median_first_reply_minutes': round(median(waits), 1) if waits else None,
                'awaiting_their_reply': awaiting, 'awaiting_our_reply': unanswered,
                'quotes': quotes[-20:], 'quotes_total': len(quotes),
            }
        return {'days': days, 'run_id': run_id, 'roles': result,
                'note': 'Times are when messages were recorded by the agent, not platform timestamps.'}

    def export_csv(self, directory, role=None, days=30):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f'messages-{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv'
        rows = self._rows(role, days)
        columns = ['role', 'counterpart', 'product', 'url', 'direction', 'kind', 'status', 'at', 'seen_at_text',
                   'fields', 'text']
        with path.open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, columns, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        return {'path': str(path), 'rows': len(rows)}
