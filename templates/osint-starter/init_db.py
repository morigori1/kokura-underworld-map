"""Initialize a fresh OSINT visualization database.

Schema is domain-agnostic — replace SITES with your investigation's sites,
and tag them with faction_tag / era_tag appropriate to your domain.

Run: python init_db.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'project.db')


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS place (
  id INTEGER PRIMARY KEY,
  name_canonical TEXT NOT NULL,
  admin_country TEXT,
  admin_state TEXT,
  centroid_lat REAL,
  centroid_lon REAL
);

CREATE TABLE IF NOT EXISTS site (
  id INTEGER PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  label TEXT NOT NULL,
  place_id INTEGER REFERENCES place(id),
  rep_lat REAL,
  rep_lon REAL,
  uncertainty_m INTEGER,
  kind TEXT,
  first_seen TEXT,
  last_seen TEXT,
  status TEXT DEFAULT 'active',
  notes TEXT,
  era_tag TEXT,
  faction_tag TEXT
);

CREATE TABLE IF NOT EXISTS source (
  id INTEGER PRIMARY KEY,
  kind TEXT,                    -- news / book / official_release / academic / ruling ...
  outlet TEXT,
  title TEXT,
  url TEXT,
  published_on TEXT
);

CREATE TABLE IF NOT EXISTS event (
  id INTEGER PRIMARY KEY,
  kind TEXT,                    -- attack / arrest / ruling / lore
  happened_on TEXT,
  site_id INTEGER REFERENCES site(id),
  title TEXT,
  summary TEXT,
  source_id INTEGER REFERENCES source(id),
  era_tag TEXT,
  faction_tag TEXT,
  severity INTEGER DEFAULT 3,
  created_by TEXT DEFAULT 'human',
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS narration (
  id INTEGER PRIMARY KEY,
  site_id INTEGER REFERENCES site(id),
  ord INTEGER DEFAULT 100,
  title TEXT,
  body TEXT,
  source_id INTEGER REFERENCES source(id),
  created_by TEXT DEFAULT 'human',
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS life_snippet (
  id INTEGER PRIMARY KEY,
  site_id INTEGER REFERENCES site(id),
  ord INTEGER DEFAULT 100,
  topic TEXT,
  text TEXT,
  source_label TEXT,
  source_url TEXT,
  created_by TEXT DEFAULT 'human',
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS local_media (
  id INTEGER PRIMARY KEY,
  site_id INTEGER REFERENCES site(id),
  kind TEXT,
  name TEXT,
  url TEXT,
  note TEXT,
  ord INTEGER DEFAULT 100,
  tier TEXT DEFAULT 'pref'
);

CREATE TABLE IF NOT EXISTS person (
  id INTEGER PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  name_kana TEXT,
  role TEXT,
  faction_tag TEXT,
  born TEXT,
  died TEXT,
  site_id INTEGER REFERENCES site(id),
  body TEXT,
  spice INTEGER DEFAULT 3,
  source_id INTEGER REFERENCES source(id)
);

CREATE TABLE IF NOT EXISTS chronicle (
  id INTEGER PRIMARY KEY,
  ord INTEGER,
  year_label TEXT,
  title TEXT,
  body TEXT,
  era_tag TEXT,
  faction_tag TEXT
);

CREATE INDEX IF NOT EXISTS idx_event_site ON event(site_id);
CREATE INDEX IF NOT EXISTS idx_narration_site ON narration(site_id);
CREATE INDEX IF NOT EXISTS idx_life_site ON life_snippet(site_id);
CREATE INDEX IF NOT EXISTS idx_local_media_site ON local_media(site_id);
"""


# === REPLACE THIS with your project's sites ===
PLACES = [
    # (name_canonical, country, state, lat, lon)
    ('Example City', 'JP', 'Example Pref', 35.6762, 139.6503),
]

SITES = [
    # (slug, label, place_idx, lat, lon, uncertainty_m, kind, first_seen, last_seen,
    #  status, notes, era_tag, faction_tag)
    ('example_landmark',
     'Example Landmark — A starting point',
     1, 35.6762, 139.6503, 100,
     'landmark', '2026', None, 'active',
     'Replace this with a real site from your investigation.'
     ' Describe the site in 1-3 sentences.',
     'era_a', 'group_alpha'),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # Schema
    for stmt in SCHEMA_SQL.strip().split(';'):
        if stmt.strip():
            cur.execute(stmt + ';')
    print('Schema created.')

    # Places
    cur.execute('DELETE FROM place')
    for p in PLACES:
        cur.execute(
            'INSERT INTO place(name_canonical, admin_country, admin_state, '
            ' centroid_lat, centroid_lon) VALUES (?,?,?,?,?)', p)

    # Sites
    cur.execute('DELETE FROM site')
    for s in SITES:
        cur.execute(
            'INSERT INTO site(slug, label, place_id, rep_lat, rep_lon, uncertainty_m, '
            ' kind, first_seen, last_seen, status, notes, era_tag, faction_tag) '
            'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', s)

    con.commit()
    counts = {t: cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
              for t in ('place', 'site', 'narration', 'event', 'source')}
    for t, n in counts.items():
        print(f'  {t}: {n} rows')
    print('init_db.py done.')
    con.close()


if __name__ == '__main__':
    main()
