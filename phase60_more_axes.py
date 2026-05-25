"""Phase 60: 5 新軸追加(decade / weapon / media_exposure / org_size / designation_status)。

既存 4 軸(economy/judicial/radius/violence_eco)と同じ tag + site_tag テーブルを使い、
canonical タグ辞書を拡張 + 343 拠点全てに backfill。

Idempotent.
"""
from __future__ import annotations
import os, re, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')
TODAY = '2026-05-25'
PROV = 'llm:claude-opus-4-7-1m'


# (axis, value, label_ja, label_en, color, ord)
NEW_TAG_DICT = [
    # === decade ===
    ('decade', '戦前',   '戦前',    'Prewar',     '#1a1a1a', 5),
    ('decade', '1940s',  '1940年代', '1940s',     '#2c3e50', 10),
    ('decade', '1950s',  '1950年代', '1950s',     '#34495e', 20),
    ('decade', '1960s',  '1960年代', '1960s',     '#7f8c8d', 30),
    ('decade', '1970s',  '1970年代', '1970s',     '#95a5a6', 40),
    ('decade', '1980s',  '1980年代', '1980s',     '#16a085', 50),
    ('decade', '1990s',  '1990年代', '1990s',     '#2980b9', 60),
    ('decade', '2000s',  '2000年代', '2000s',     '#3498db', 70),
    ('decade', '2010s',  '2010年代', '2010s',     '#9b59b6', 80),
    ('decade', '2020s',  '2020年代', '2020s',     '#e74c3c', 90),

    # === weapon / method(手口)===
    ('weapon', '銃器',         '銃器',         'Firearms',     '#c0392b', 10),
    ('weapon', '刃物',         '刃物',         'Blades',       '#e74c3c', 20),
    ('weapon', '鈍器',         '鈍器',         'Blunt',        '#d35400', 30),
    ('weapon', '火器・爆発物', '火器・爆発物', 'Fire/explosive', '#e67e22', 40),
    ('weapon', '物理威迫',     '物理威迫',     'Intimidation', '#f39c12', 50),
    ('weapon', '詐欺',         '詐欺',         'Fraud',        '#3498db', 60),
    ('weapon', 'SNS闇バイト',  'SNS闇バイト',  'SNS dark job', '#2980b9', 70),
    ('weapon', '麻薬密輸',     '麻薬密輸',     'Drug smuggle', '#9b59b6', 80),
    ('weapon', 'マネロン',     'マネロン',     'Money laundering', '#8e44ad', 90),
    ('weapon', 'カジノ',       'カジノ',       'Casino',       '#16a085', 100),
    ('weapon', 'みかじめ料徴収','みかじめ料徴収','Protection',  '#c0392b', 110),
    ('weapon', '政治献金',     '政治献金',     'Political $',  '#34495e', 120),
    ('weapon', '行政・司法',   '行政・司法',   'Admin/judicial', '#27ae60', 130),
    ('weapon', '非犯罪',       '非犯罪',       'Non-criminal', '#bdc3c7', 999),

    # === media_exposure(報道露出度)===
    ('media_exposure', '国際多重報道',     '国際多重報道',   'Intl massive',     '#c0392b', 10),
    ('media_exposure', '全国多重報道',     '全国多重報道',   'Nat\'l massive',   '#e74c3c', 20),
    ('media_exposure', '全国紙複数',       '全国紙複数',     'Multi national',   '#e67e22', 30),
    ('media_exposure', '全国紙単発',       '全国紙単発',     'Single national',  '#f39c12', 40),
    ('media_exposure', '地方紙のみ',       '地方紙のみ',     'Regional only',    '#3498db', 50),
    ('media_exposure', '書籍のみ',         '書籍のみ',       'Books only',       '#9b59b6', 60),
    ('media_exposure', '学術論文のみ',     '学術論文のみ',   'Academic only',    '#16a085', 70),
    ('media_exposure', '専門誌のみ',       '専門誌のみ',     'Specialty mag',    '#27ae60', 80),
    ('media_exposure', '公的記録のみ',     '公的記録のみ',   'Official only',    '#7f8c8d', 90),
    ('media_exposure', '未報道',           '未報道',         'Unreported',       '#bdc3c7', 999),

    # === org_size(組織規模)===
    ('org_size', '大規模指定暴力団', '大規模指定暴力団(1000+)', 'Major (1000+)',  '#c0392b', 10),
    ('org_size', '中規模指定暴力団', '中規模指定暴力団(100-1000)', 'Mid (100-1000)', '#e67e22', 20),
    ('org_size', '小規模組織',       '小規模組織(<100)',     'Small (<100)',    '#f39c12', 30),
    ('org_size', 'トクリュウ流動集団', 'トクリュウ流動集団',  'Tokuryu fluid',   '#ff6b35', 40),
    ('org_size', '半グレ連合',       '半グレ連合',          'Hangure coalition', '#e67e22', 50),
    ('org_size', '個人犯罪',         '個人犯罪',            'Individual crime', '#9b59b6', 60),
    ('org_size', '解散済',           '解散済',              'Disbanded',        '#7f8c8d', 70),
    ('org_size', '非該当',           '非該当',              'N/A',              '#bdc3c7', 999),

    # === designation_status(規制カテゴリ)===
    ('designation_status', '特定危険指定暴力団',   '特定危険指定暴力団',   'Specifically Dangerous', '#c0392b', 10),
    ('designation_status', '特定抗争指定暴力団',   '特定抗争指定暴力団',   'Specified Warring',     '#e74c3c', 20),
    ('designation_status', '通常指定暴力団',       '通常指定暴力団',       'Designated',            '#e67e22', 30),
    ('designation_status', '準暴力団',             '準暴力団',             'Quasi (hangure)',       '#f39c12', 40),
    ('designation_status', 'トクリュウ概念',       'トクリュウ概念',       'Tokuryu',               '#ff6b35', 50),
    ('designation_status', 'OFAC TCO指定',         'OFAC TCO指定',         'OFAC TCO',              '#9b59b6', 60),
    ('designation_status', '非指定(民事のみ)',     '非指定(民事のみ)',     'Civil only',            '#bdc3c7', 70),
    ('designation_status', '不適用',               '不適用',               'N/A',                   '#ecf0f1', 999),
]


def decade_from_year_string(s):
    if not s: return None
    m = re.search(r'(\d{4})', s)
    if not m: return None
    y = int(m.group(1))
    if y < 1940: return '戦前'
    return f'{(y // 10) * 10}s'


def infer_tags(site):
    """site dict → {axis: [values]}"""
    slug = site['slug']
    kind = site['kind'] or ''
    faction = site['faction_tag'] or ''
    era = site['era_tag'] or ''
    notes = (site['notes'] or '').lower()
    label = (site['label'] or '').lower()
    fs = site.get('first_seen') or ''
    label_text = label + ' ' + notes

    tags = {'decade': [], 'weapon': [], 'media_exposure': [],
            'org_size': [], 'designation_status': []}

    # === decade ===
    d = decade_from_year_string(fs)
    if not d:
        d = decade_from_year_string(label_text)
    if not d:
        # era_tag fallback
        era_to_decade = {
            '戦後闇市': '1940s', '高度成長': '1960s', '平成抗争': '2000s',
            '頂上作戦': '2010s', '解体後': '2020s',
        }
        d = era_to_decade.get(era, '2010s')
    tags['decade'] = [d]

    # === weapon / method ===
    if '銃器' in label_text or '射殺' in label_text or '発砲' in label_text \
       or '銃撃' in label_text:
        tags['weapon'].append('銃器')
    if '刃物' in label_text or '刺' in label_text:
        tags['weapon'].append('刃物')
    if '金属バット' in label_text or '鈍器' in label_text or '殴打' in label_text \
       or '殴' in label_text:
        tags['weapon'].append('鈍器')
    if '火災' in label_text or '放火' in label_text or '爆破' in label_text \
       or '爆発' in label_text:
        tags['weapon'].append('火器・爆発物')
    if 'みかじめ' in label_text or '徴収' in label_text:
        tags['weapon'].append('みかじめ料徴収')
    if 'マネロン' in label_text or 'マネー' in label_text or '仮想通貨' in label_text \
       or 'ミキシング' in label_text:
        tags['weapon'].append('マネロン')
    if '麻薬' in label_text or '薬物' in label_text or '覚せい剤' in label_text \
       or 'ヒロポン' in label_text or '大麻' in label_text or '密輸' in label_text:
        tags['weapon'].append('麻薬密輸')
    if 'カジノ' in label_text:
        tags['weapon'].append('カジノ')
    if 'sns' in label_text or '闇バイト' in label_text or 'リクルーター' in label_text \
       or 'トクリュウ' in label_text:
        tags['weapon'].append('SNS闇バイト')
    if '詐欺' in label_text or 'ロマンス' in label_text or '特殊詐欺' in label_text:
        tags['weapon'].append('詐欺')
    if '政治' in label_text or '献金' in label_text or 'ロッキード' in label_text:
        tags['weapon'].append('政治献金')

    if not tags['weapon']:
        if kind == 'attack_site':
            if faction in ('工藤組系', '田中組系', '草野一家系', '道仁会系'):
                tags['weapon'] = ['銃器', '物理威迫']
            elif faction in ('半グレ', 'トクリュウ'):
                tags['weapon'] = ['鈍器', '物理威迫']
            else:
                tags['weapon'] = ['物理威迫']
        elif kind in ('ruling',) or faction in ('司法側', '県警側'):
            tags['weapon'] = ['行政・司法']
        elif faction in ('市民側', '著作者'):
            tags['weapon'] = ['非犯罪']
        else:
            tags['weapon'] = ['物理威迫']

    # === media_exposure ===
    # 国際メディアに載った
    if 'ofac' in label_text or 'rico' in label_text or 'compound' in label_text \
       or 'ルフィ' in label_text or '海老蔵' in label_text:
        tags['media_exposure'] = ['国際多重報道']
    # 全国大事件
    elif '頂上作戦' in label_text or '本部解体' in label_text or '神戸山口組分裂' in label_text \
         or '阪神大震災' in label_text or 'ロッキード' in label_text or 'みずほ' in label_text \
         or '広島抗争' in label_text or '山一抗争' in label_text or '黒い霧' in label_text:
        tags['media_exposure'] = ['全国多重報道']
    # 全国紙複数
    elif kind == 'attack_site' and faction in ('工藤組系', 'トクリュウ', '半グレ'):
        tags['media_exposure'] = ['全国紙複数']
    elif kind in ('hq_former', 'hq_current'):
        tags['media_exposure'] = ['全国紙複数']
    # 学術
    elif kind == 'lore_site' and faction == '著作者':
        tags['media_exposure'] = ['書籍のみ']
    # 公的
    elif faction in ('司法側', '県警側'):
        tags['media_exposure'] = ['公的記録のみ']
    # 市民・文化
    elif faction in ('市民側',):
        if kind == 'district':
            tags['media_exposure'] = ['地方紙のみ']
        else:
            tags['media_exposure'] = ['地方紙のみ']
    else:
        tags['media_exposure'] = ['地方紙のみ']

    # === org_size ===
    if faction == '山口組系' and ('総本部' in label or '本部' in label):
        tags['org_size'] = ['大規模指定暴力団']
    elif faction in ('工藤組系', '草野一家系', '田中組系'):
        if 'hq_former' in kind or 'hq_current' in kind:
            tags['org_size'] = ['中規模指定暴力団']
        else:
            tags['org_size'] = ['中規模指定暴力団']
    elif faction == '道仁会系':
        tags['org_size'] = ['中規模指定暴力団']
    elif faction == '福博会系':
        tags['org_size'] = ['小規模組織']
    elif faction in ('司法側', '県警側'):
        tags['org_size'] = ['非該当']
    elif faction in ('市民側', '著作者'):
        tags['org_size'] = ['非該当']
    elif faction == 'トクリュウ':
        tags['org_size'] = ['トクリュウ流動集団']
    elif faction == '半グレ':
        tags['org_size'] = ['半グレ連合']
    elif faction == '中国系':
        tags['org_size'] = ['半グレ連合']
    else:
        tags['org_size'] = ['非該当']

    # 解散済の override
    if '解散' in label_text or '解体' in label_text or '関東連合' in label_text:
        tags['org_size'] = ['解散済']

    # === designation_status ===
    if '工藤' in label_text and ('本部' in label_text or 'kandake' in slug):
        tags['designation_status'] = ['特定危険指定暴力団']
    elif faction == '工藤組系':
        tags['designation_status'] = ['特定危険指定暴力団']
    elif faction == '山口組系' and ('神戸' in label or '六代目' in label or '神戸山口組' in label):
        tags['designation_status'] = ['特定抗争指定暴力団']
    elif faction in ('山口組系',):
        tags['designation_status'] = ['通常指定暴力団']
    elif faction in ('道仁会系', '福博会系'):
        tags['designation_status'] = ['通常指定暴力団']
    elif faction in ('半グレ',):
        tags['designation_status'] = ['準暴力団']
    elif faction in ('トクリュウ',):
        tags['designation_status'] = ['トクリュウ概念']
    elif faction in ('中国系',):
        tags['designation_status'] = ['準暴力団']
    elif faction in ('司法側', '県警側', '市民側', '著作者'):
        tags['designation_status'] = ['不適用']
    else:
        tags['designation_status'] = ['不適用']

    # OFAC 指定追加
    if 'ofac' in label_text or 'tco' in label_text:
        if '特定危険指定暴力団' in tags['designation_status']:
            tags['designation_status'].append('OFAC TCO指定')

    return tags


# 明示的 override
EXPLICIT = {
    'kudokai_hq_kandake': {
        'decade': ['1980s', '1990s', '2000s', '2010s'],  # 1987 結成 → 2019 解体
        'weapon': ['銃器', 'みかじめ料徴収', '物理威迫'],
        'media_exposure': ['国際多重報道'],
        'org_size': ['中規模指定暴力団'],
        'designation_status': ['特定危険指定暴力団', 'OFAC TCO指定'],
    },
    'shutoken_serial_2024': {
        'decade': ['2020s'],
        'weapon': ['SNS闇バイト', '鈍器', '物理威迫'],
        'media_exposure': ['全国多重報道'],
        'org_size': ['トクリュウ流動集団'],
        'designation_status': ['トクリュウ概念'],
    },
    'komae_robbery_2023': {
        'decade': ['2020s'],
        'weapon': ['SNS闇バイト', '鈍器'],
        'media_exposure': ['国際多重報道'],
        'org_size': ['トクリュウ流動集団'],
        'designation_status': ['トクリュウ概念'],
    },
    'kobe_yamaguchi_souhonbu': {
        'decade': ['1940s', '1950s', '1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s'],
        'weapon': ['銃器', 'みかじめ料徴収'],
        'media_exposure': ['全国多重報道'],
        'org_size': ['大規模指定暴力団'],
        'designation_status': ['特定抗争指定暴力団'],
    },
    'attack_2014_dentist': {
        'decade': ['2010s'],
        'weapon': ['銃器'],
        'media_exposure': ['全国多重報道'],
        'org_size': ['非該当'],
        'designation_status': ['不適用'],
    },
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # === 1) canonical tag dict 追加 ===
    for axis, value, ja, en, color, ord_ in NEW_TAG_DICT:
        cur.execute(
            'INSERT INTO tag(axis, value, label_ja, label_en, color, ord) '
            'VALUES (?,?,?,?,?,?) '
            'ON CONFLICT(axis, value) DO UPDATE SET '
            ' label_ja=excluded.label_ja, label_en=excluded.label_en, '
            ' color=excluded.color, ord=excluded.ord',
            (axis, value, ja, en, color, ord_))
    print(f'New tag dict entries: {len(NEW_TAG_DICT)}')

    # === 2) tag id 検索 ===
    tag_lookup = {(r[1], r[2]): r[0] for r in cur.execute(
        'SELECT id, axis, value FROM tag').fetchall()}

    # === 3) 新軸の既存 backfill を削除して再生成 ===
    new_axes = ('decade', 'weapon', 'media_exposure', 'org_size', 'designation_status')
    cur.execute(
        'DELETE FROM site_tag WHERE tag_id IN '
        '(SELECT id FROM tag WHERE axis IN (?, ?, ?, ?, ?))', new_axes)

    sites = cur.execute(
        'SELECT id, slug, label, kind, faction_tag, era_tag, notes, first_seen '
        'FROM site').fetchall()
    sites_dicts = [
        {'id': r[0], 'slug': r[1], 'label': r[2], 'kind': r[3],
         'faction_tag': r[4], 'era_tag': r[5], 'notes': r[6], 'first_seen': r[7]}
        for r in sites]

    n_inserted = 0
    for site in sites_dicts:
        if site['slug'] in EXPLICIT:
            tags = EXPLICIT[site['slug']]
        else:
            tags = infer_tags(site)
        for axis, values in tags.items():
            for value in values:
                tag_id = tag_lookup.get((axis, value))
                if tag_id is None:
                    print(f'WARN: unknown tag {axis}={value} for {site["slug"]}')
                    continue
                cur.execute(
                    'INSERT OR IGNORE INTO site_tag(site_id, tag_id, created_by, created_at) '
                    'VALUES (?,?,?,?)',
                    (site['id'], tag_id, PROV, TODAY))
                n_inserted += 1
    con.commit()

    # === 4) 統計 ===
    total = cur.execute('SELECT COUNT(*) FROM site').fetchone()[0]
    print(f'\nphase60: +{n_inserted} site_tag rows for new 5 axes')
    print()
    for axis in new_axes:
        covered = cur.execute(
            'SELECT COUNT(DISTINCT st.site_id) FROM site_tag st '
            'JOIN tag t ON st.tag_id = t.id WHERE t.axis = ?', (axis,)).fetchone()[0]
        print(f'  {axis}: {covered}/{total} ({100*covered/total:.0f}%)')
        # Top 5 values
        rows = cur.execute(
            'SELECT t.value, COUNT(*) FROM site_tag st '
            'JOIN tag t ON st.tag_id = t.id WHERE t.axis = ? '
            'GROUP BY t.value ORDER BY 2 DESC LIMIT 5', (axis,)).fetchall()
        for v, c in rows:
            print(f'    {v}: {c}')
    con.close()


if __name__ == '__main__':
    main()
