"""Phase 01: Add narration + sample event for the starter sites.

This is the canonical phase script pattern:
  1. Open DB
  2. Look up site IDs by slug
  3. For each (slug, payload) in your data dict:
     - DELETE existing rows matching your marker
     - INSERT fresh rows
  4. Commit and report

Idempotent: re-running replaces this phase's own rows without touching others.

Run: python phase01_basic.py
"""
from __future__ import annotations
import os, sqlite3
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'project.db')

PROVENANCE = 'human:your_name'  # Replace; or 'llm:claude-opus-4-7' if generated
TODAY = date.today().isoformat()


NARRATIONS = {
    'example_landmark': [
        # (ord, title, body)
        (10, 'Overview',
         'A brief overview paragraph describing this site. '
         'Replace with your own content.'),
        (20, 'Historical context',
         'Additional context paragraph — historical background, why this site matters.'),
    ],
}

EVENTS = [
    # (site_slug, kind, happened_on, title, summary, era_tag, faction_tag, severity)
    ('example_landmark', 'lore', '2026-01-01',
     'Project started',
     'A placeholder event. Replace with real events from your investigation.',
     'era_a', 'group_alpha', 3),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    sites = {r[1]: r[0] for r in cur.execute('SELECT id, slug FROM site')}

    n_inserted = 0
    for slug, rows in NARRATIONS.items():
        sid = sites.get(slug)
        if sid is None:
            print(f'WARN: site slug not found: {slug}')
            continue
        for ord_, title, body in rows:
            cur.execute('DELETE FROM narration WHERE site_id=? AND ord=?', (sid, ord_))
            cur.execute(
                'INSERT INTO narration(site_id, ord, title, body, created_by, created_at) '
                'VALUES (?,?,?,?,?,?)',
                (sid, ord_, title, body, PROVENANCE, TODAY))
            n_inserted += 1

    e_inserted = 0
    for slug, kind, date_, title, summary, era, faction, sev in EVENTS:
        sid = sites.get(slug)
        if sid is None: continue
        cur.execute(
            'DELETE FROM event WHERE site_id=? AND happened_on=? AND title=?',
            (sid, date_, title))
        cur.execute(
            'INSERT INTO event(site_id, kind, happened_on, title, summary, '
            ' era_tag, faction_tag, severity, created_by, created_at) '
            'VALUES (?,?,?,?,?,?,?,?,?,?)',
            (sid, kind, date_, title, summary, era, faction, sev, PROVENANCE, TODAY))
        e_inserted += 1

    con.commit()
    print(f'phase01_basic: +{n_inserted} narration, +{e_inserted} events')
    con.close()


if __name__ == '__main__':
    main()
