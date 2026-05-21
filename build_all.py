"""Rebuild every derived data layer and the dashboard, from the base kokura.db.

Run order matters:
  - phase5 builds POIs that phase4 centers on
  - phase6 builds the event source rows that phase8 enriches with og:image

Each phase is idempotent (re-running replaces its own rows) and hits public APIs,
so a full run takes several minutes and needs an internet connection.

Usage:
  python build_all.py          # init DB if needed, run every phase, rebuild index.html
  python build_all.py dash     # only rebuild index.html from current DB
  python build_all.py init     # only (re)seed the base kokura.db
"""
from __future__ import annotations
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))

PHASES = [
    ('phase5_poi.py',          'POI + narration + era captions'),
    ('phase4_wayback.py',      'Wayback historical-satellite frames'),
    ('phase6_events.py',       'curated news / ruling events'),
    ('phase7_images.py',       'Wikimedia Commons location images'),
    ('phase8_event_images.py', 'per-event preview images (og:image)'),
    ('phase9_testimony.py',    'victim testimony + ruling excerpts'),
    ('phase10_local_life.py',  'local-life spots + daily-life snippets'),
    ('phase11_lore.py',        'lore / gossip layer'),
    ('phase12_diverse.py',     'diverse-source layer (OFAC / foreign press / books / academic / documentaries)'),
    ('phase13_persons.py',     'persons + org tree'),
    ('phase14_national.py',    'national yakuza context (Yamaguchi-gumi splits, anti-yakuza law, Kyushu war)'),
    ('phase15_micro.py',       'micro events + supplementary lore (year-by-year gaps)'),
    ('phase16_crime_stats.py', 'crime stat time series (NPA white papers)'),
    ('phase17_neighborhood.py','neighborhood-level micro events + lore (town/street-level)'),
    ('phase18_thicker.py',     'prewar history + food + family + media + national/international comparison + finance'),
    ('phase19_kurume.py',      'Kurume / Dojinkai / Namikawakai — 九州抗争 detail'),
    ('phase20_kobe.py',        'Kobe / Yamaguchi-gumi — 1915-2024 (山一抗争, 神戸山口組分裂, 絆會)'),
    ('phase21_tokyo.py',       'Tokyo / Sumiyoshi-kai / Inagawa-kai + regulatory hubs (Diet, NPA, FSA)'),
    ('phase22_hiroshima.py',   'Hiroshima / Kyoseikai (広島抗争・仁義なき戦い・孤狼の血)'),
    ('phase23_hangure.py',     'Hangure / Tokuryu — 半グレ・準暴力団・トクリュウ(関東連合・ルフィ事件・連続強盗・闇バイト)'),
    ('phase24_more_cases.py',  'Hangure/Tokuryu individual cases + 沖縄/京都/名古屋/大阪 regional sites'),
    ('phase25_individual_cases.py', '報道で実名公開済の個別事案(海老蔵事件・ルフィ事件被告・各県強盗等)'),
    ('phase26_thematic.py',    '経済/政治/興行/スポーツ/薬物/戦後初期抗争のテーマ深掘り(神戸芸能社・児玉誉士夫・ロッキード・バブル地上げ・阪神大震災・黒い霧・大相撲野球賭博・覚せい剤戦後史)'),
    ('dash5.py',               'render index.html'),
]


def run(script: str, desc: str, idx: int, total: int) -> None:
    path = os.path.join(HERE, script)
    if not os.path.exists(path):
        print(f'  [{idx}/{total}] {script} — (skipped: not yet implemented)')
        return
    print(f'\n=== [{idx}/{total}] {script} — {desc} ===', flush=True)
    t = time.time()
    result = subprocess.run([sys.executable, path], cwd=HERE)
    if result.returncode != 0:
        sys.exit(f'ERROR: {script} failed (exit code {result.returncode}).')
    print(f'--- {script} done in {time.time() - t:.0f}s ---', flush=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if mode == 'init':
        run('init_db.py', 'create / refresh kokura.db schema and base seeds', 1, 1)
        return

    # ensure DB exists; if missing, run init_db.py first
    db = os.path.join(HERE, 'kokura.db')
    if not os.path.exists(db):
        print('kokura.db missing — running init_db.py first.')
        run('init_db.py', 'create kokura.db', 0, 0)

    if mode == 'dash':
        steps = [PHASES[-1]]
    else:
        steps = PHASES

    start = time.time()
    for i, (script, desc) in enumerate(steps, 1):
        run(script, desc, i, len(steps))
    print(f'\nAll done in {time.time() - start:.0f}s. Open index.html in a browser.')


if __name__ == '__main__':
    main()
