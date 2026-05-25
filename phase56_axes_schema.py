"""Phase 56: 5 軸追加 — schema + tag/site_tag/site_link テーブル + 標準タグ投入。

新規 5 軸:
  1. economy        — 資金源タイプ(薬物/みかじめ料/建設/IT詐欺 etc.)
  2. judicial       — 司法状態(未起訴/公判中/判決済 etc.)
  3. radius         — 影響圏(全国/広域/県内/市内/町内/国際)
  4. violence_eco   — 暴力 vs 経済(暴力中心/経済中心/両方/いずれでもない)
  5. intl_link      — 国際接続(site_link 関係テーブル)

スキーマ方針:
  - 1-4 は汎用 tag + site_tag(多対多)で吸収。将来軸追加で migration 不要
  - 5 は site_link(関係)で線描画用に独立

実際の値割り当てバックフィルは phase57 / phase58 に分離。
このフェーズは構造と canonical タグ辞書のみ。

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tag (
  id INTEGER PRIMARY KEY,
  axis TEXT NOT NULL,            -- 'economy' / 'judicial' / 'radius' / 'violence_eco'
  value TEXT NOT NULL,           -- '薬物' / '判決済' / '広域' etc.
  label_ja TEXT,
  label_en TEXT,
  color TEXT,                    -- ヘックスカラー(色分けモード時)
  ord INTEGER DEFAULT 100,       -- 表示順
  UNIQUE(axis, value)
);

CREATE TABLE IF NOT EXISTS site_tag (
  site_id INTEGER NOT NULL,
  tag_id INTEGER NOT NULL,
  created_by TEXT DEFAULT 'llm:claude-opus-4-7-1m',
  created_at TEXT,
  PRIMARY KEY (site_id, tag_id),
  FOREIGN KEY (site_id) REFERENCES site(id),
  FOREIGN KEY (tag_id) REFERENCES tag(id)
);
CREATE INDEX IF NOT EXISTS idx_site_tag_site ON site_tag(site_id);
CREATE INDEX IF NOT EXISTS idx_site_tag_tag ON site_tag(tag_id);

CREATE TABLE IF NOT EXISTS site_link (
  id INTEGER PRIMARY KEY,
  from_site_id INTEGER NOT NULL,
  to_site_id INTEGER NOT NULL,
  kind TEXT,                     -- 'indo_intl' / 'sanction' / 'compound_route' / 'split' etc.
  note TEXT,
  source_id INTEGER,
  created_by TEXT DEFAULT 'llm:claude-opus-4-7-1m',
  created_at TEXT,
  FOREIGN KEY (from_site_id) REFERENCES site(id),
  FOREIGN KEY (to_site_id) REFERENCES site(id),
  FOREIGN KEY (source_id) REFERENCES source(id)
);
CREATE INDEX IF NOT EXISTS idx_site_link_from ON site_link(from_site_id);
CREATE INDEX IF NOT EXISTS idx_site_link_to ON site_link(to_site_id);
"""


# canonical tag dictionary
# (axis, value, label_ja, label_en, color, ord)
TAG_DICT = [
    # === economy(資金源タイプ)===
    ('economy', '薬物',         '薬物',         'Drugs',         '#9b59b6', 10),
    ('economy', 'みかじめ料',   'みかじめ料',   'Protection',    '#d9534f', 20),
    ('economy', '建設業',       '建設業',       'Construction',  '#e67e22', 30),
    ('economy', '不動産・地上げ', '不動産・地上げ', 'Real estate',  '#d35400', 40),
    ('economy', '金融・銀行',   '金融・銀行',   'Banking',       '#16a085', 50),
    ('economy', 'IT詐欺',       'IT・特殊詐欺', 'IT/wire fraud', '#3498db', 60),
    ('economy', '興行・芸能',   '興行・芸能',   'Entertainment', '#e91e63', 70),
    ('economy', '政治献金',     '政治献金',     'Political $',   '#34495e', 80),
    ('economy', 'マネロン',     'マネロン',     'Money laundry', '#7f8c8d', 90),
    ('economy', '港湾労働',     '港湾労働',     'Port labor',    '#2980b9', 100),
    ('economy', '闇市・露店',   '闇市・露店',   'Black market',  '#c0392b', 110),
    ('economy', 'カジノ',       'カジノ',       'Casino',        '#f39c12', 120),
    ('economy', '資金源なし',   '資金源なし',   'No revenue',    '#bdc3c7', 999),

    # === judicial(司法状態)===
    ('judicial', '未起訴',     '未起訴',     'Not indicted',   '#bdc3c7', 10),
    ('judicial', '起訴済',     '起訴済',     'Indicted',       '#f39c12', 20),
    ('judicial', '公判中',     '公判中',     'In trial',       '#e67e22', 30),
    ('judicial', '一審判決済', '一審判決済', '1st verdict',    '#3498db', 40),
    ('judicial', '控訴中',     '控訴中',     'Appeal pending', '#2980b9', 50),
    ('judicial', '上告中',     '上告中',     'Supreme review', '#1abc9c', 60),
    ('judicial', '確定済',     '確定済',     'Final',          '#27ae60', 70),
    ('judicial', '時効',       '時効',       'Time-barred',    '#7f8c8d', 80),
    ('judicial', '不起訴',     '不起訴',     'Declined',       '#95a5a6', 90),
    ('judicial', '行政処分のみ', '行政処分のみ', 'Admin penalty', '#9b59b6', 100),
    ('judicial', '刑事事件外', '刑事事件外', 'Non-criminal',   '#ecf0f1', 999),

    # === radius(影響圏)===
    ('radius', '町内',  '町内',  'Neighborhood',  '#d9534f', 10),
    ('radius', '市内',  '市内',  'City',          '#e67e22', 20),
    ('radius', '県内',  '県内',  'Prefecture',    '#f39c12', 30),
    ('radius', '広域',  '広域',  'Multi-pref',    '#3498db', 40),
    ('radius', '全国',  '全国',  'Nationwide',    '#9b59b6', 50),
    ('radius', '国際',  '国際',  'International', '#1abc9c', 60),

    # === violence_eco(暴力 vs 経済)===
    ('violence_eco', '暴力中心',     '暴力中心',     'Violent',     '#c0392b', 10),
    ('violence_eco', '経済中心',     '経済中心',     'Economic',    '#3498db', 20),
    ('violence_eco', '両方',         '両方',         'Both',        '#9b59b6', 30),
    ('violence_eco', '司法・行政',   '司法・行政',   'Judicial',    '#16a085', 40),
    ('violence_eco', '市民・文化',   '市民・文化',   'Civic',       '#27ae60', 50),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    for stmt in SCHEMA_SQL.strip().split(';'):
        if stmt.strip():
            cur.execute(stmt + ';')
    print('Schema created/verified')

    # canonical tag dict
    n = 0
    for axis, value, ja, en, color, ord_ in TAG_DICT:
        cur.execute(
            'INSERT INTO tag(axis, value, label_ja, label_en, color, ord) '
            'VALUES (?,?,?,?,?,?) '
            'ON CONFLICT(axis, value) DO UPDATE SET '
            ' label_ja=excluded.label_ja, label_en=excluded.label_en, '
            ' color=excluded.color, ord=excluded.ord',
            (axis, value, ja, en, color, ord_))
        n += 1
    con.commit()
    print(f'Tag dict: {n} entries')

    # Per-axis count
    for axis in ('economy', 'judicial', 'radius', 'violence_eco'):
        c = cur.execute('SELECT COUNT(*) FROM tag WHERE axis = ?', (axis,)).fetchone()[0]
        print(f'  {axis}: {c} values')

    con.close()


if __name__ == '__main__':
    main()
