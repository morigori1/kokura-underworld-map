"""Phase 59: phase57 で軸欠落した 7 拠点のギャップを埋める。

EXPLICIT_TAGS で 3 軸だけ指定した拠点に対して、残り 1 軸を heuristics で補完。

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')
TODAY = '2026-05-25'
PROV = 'llm:claude-opus-4-7-1m'


# (slug, axis, value)
GAP_FILLS = [
    # 4 市民襲撃事件: economy は「みかじめ料」(工藤會の主要資金源を狙う威迫)
    ('attack_1998_ashiya_fisheries', 'economy', 'みかじめ料'),
    ('attack_2012_ex_officer',       'economy', 'みかじめ料'),
    ('attack_2013_nurse',            'economy', 'みかじめ料'),
    # 司法・行政機関: 「資金源なし」
    ('fukuoka_kenkei',         'economy', '資金源なし'),
    ('kokura_district_court',  'economy', '資金源なし'),
    # 薬物密輸ルート: 司法状態 = 確定済(継続摘発あり)
    ('drug_china_southeast',   'judicial', '確定済'),
    ('drug_korea_route',       'judicial', '確定済'),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    sites = {r[1]: r[0] for r in cur.execute('SELECT id, slug FROM site')}
    tag_lookup = {(r[1], r[2]): r[0] for r in cur.execute(
        'SELECT id, axis, value FROM tag').fetchall()}

    n = 0
    for slug, axis, value in GAP_FILLS:
        sid = sites.get(slug)
        if sid is None:
            print(f'WARN: unknown slug {slug}'); continue
        tid = tag_lookup.get((axis, value))
        if tid is None:
            print(f'WARN: unknown tag {axis}={value}'); continue
        cur.execute(
            'INSERT OR IGNORE INTO site_tag(site_id, tag_id, created_by, created_at) '
            'VALUES (?,?,?,?)', (sid, tid, PROV, TODAY))
        n += 1
    con.commit()

    # 確認
    total = cur.execute('SELECT COUNT(*) FROM site').fetchone()[0]
    full = cur.execute('''
        SELECT COUNT(*) FROM (
          SELECT st.site_id FROM site_tag st JOIN tag t ON st.tag_id = t.id
          WHERE t.axis IN ('economy','judicial','radius','violence_eco')
          GROUP BY st.site_id HAVING COUNT(DISTINCT t.axis) = 4
        )
    ''').fetchone()[0]
    print(f'phase59_axis_gapfill: +{n} rows')
    print(f'  全 4 軸カバー: {full}/{total} ({100*full/total:.0f}%)')
    con.close()


if __name__ == '__main__':
    main()
