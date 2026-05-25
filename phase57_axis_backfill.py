"""Phase 57: 全 343 拠点に 4 軸のタグを backfill。

ヒューリスティクスで一括割り当て:
  - 既存 site.kind / faction_tag / era_tag / notes から推定
  - 1 拠点に複数 economy タグも可
  - 全エントリ created_by='llm:claude-opus-4-7-1m'(provenance 列)

明示的な site-specific override が必要なものは個別マッピング。
Idempotent: re-run で site_tag を全消去 → 再生成。
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')
TODAY = '2026-05-25'
PROV = 'llm:claude-opus-4-7-1m'


# slug → {axis: [values]} 個別 override(ヒューリスティクスより優先)
EXPLICIT_TAGS = {
    'kudokai_hq_kandake': {
        'economy': ['みかじめ料', '建設業', '金融・銀行', '政治献金'],
        'judicial': ['確定済'],
        'radius': ['広域'],
        'violence_eco': ['両方'],
    },
    'kudokai_hq_kandake_signboard': {
        'economy': ['みかじめ料'],
        'judicial': ['確定済'],
        'radius': ['町内'],
        'violence_eco': ['暴力中心'],
    },
    'attack_2014_dentist': {
        'economy': ['みかじめ料'],
        'judicial': ['確定済'],
        'radius': ['市内'],
        'violence_eco': ['暴力中心'],
    },
    'attack_2013_nurse': {
        'judicial': ['確定済'], 'radius': ['市内'], 'violence_eco': ['暴力中心'],
    },
    'attack_2012_ex_officer': {
        'judicial': ['確定済'], 'radius': ['市内'], 'violence_eco': ['暴力中心'],
    },
    'attack_1998_ashiya_fisheries': {
        'judicial': ['確定済'], 'radius': ['県内'], 'violence_eco': ['暴力中心'],
    },
    'kokura_district_court': {
        'judicial': ['確定済'], 'radius': ['広域'], 'violence_eco': ['司法・行政'],
    },
    'fukuoka_kenkei': {
        'judicial': ['確定済'], 'radius': ['広域'], 'violence_eco': ['司法・行政'],
    },
    'ofac_treasury_designation': {
        'economy': ['マネロン'],
        'judicial': ['行政処分のみ'],
        'radius': ['国際'],
        'violence_eco': ['司法・行政'],
    },
    'komae_robbery_2023': {
        'economy': ['IT詐欺'],
        'judicial': ['公判中'],
        'radius': ['広域'],
        'violence_eco': ['暴力中心'],
    },
    'philippines_luffy_base': {
        'economy': ['IT詐欺'],
        'judicial': ['公判中'],
        'radius': ['国際'],
        'violence_eco': ['経済中心'],
    },
    'tokyo_kabukicho': {
        'economy': ['みかじめ料', '興行・芸能', '薬物'],
        'judicial': ['刑事事件外'],
        'radius': ['全国'],
        'violence_eco': ['両方'],
    },
    'roppongi_clubs_hangure': {
        'economy': ['興行・芸能', 'みかじめ料'],
        'judicial': ['確定済'],
        'radius': ['全国'],
        'violence_eco': ['両方'],
    },
    'kobe_yamaguchi_souhonbu': {
        'economy': ['みかじめ料', '建設業', '不動産・地上げ', '興行・芸能', '金融・銀行'],
        'judicial': ['行政処分のみ'],
        'radius': ['全国'],
        'violence_eco': ['両方'],
    },
    'mizuho_bank_hq': {
        'economy': ['金融・銀行'],
        'judicial': ['行政処分のみ'],
        'radius': ['全国'],
        'violence_eco': ['司法・行政'],
    },
    'bubble_jiage': {
        'economy': ['不動産・地上げ'],
        'judicial': ['確定済'],
        'radius': ['全国'],
        'violence_eco': ['経済中心'],
    },
    'jusen_jutaku': {
        'economy': ['金融・銀行', '不動産・地上げ'],
        'judicial': ['行政処分のみ'],
        'radius': ['全国'],
        'violence_eco': ['経済中心'],
    },
    'kobe_geinosha': {
        'economy': ['興行・芸能'],
        'judicial': ['刑事事件外'],
        'radius': ['全国'],
        'violence_eco': ['経済中心'],
    },
    'lockheed_scandal': {
        'economy': ['政治献金'],
        'judicial': ['確定済'],
        'radius': ['全国'],
        'violence_eco': ['経済中心'],
    },
    'kodama_yoshio_residence': {
        'economy': ['政治献金'],
        'judicial': ['不起訴'],
        'radius': ['全国'],
        'violence_eco': ['経済中心'],
    },
    'crypto_mixing_takedown_2025': {
        'economy': ['マネロン', 'IT詐欺'],
        'judicial': ['公判中'],
        'radius': ['全国'],
        'violence_eco': ['経済中心'],
    },
    'cambodia_compounds_link': {
        'economy': ['IT詐欺', 'マネロン'],
        'judicial': ['刑事事件外'],
        'radius': ['国際'],
        'violence_eco': ['経済中心'],
    },
    'myanmar_compounds_link': {
        'economy': ['IT詐欺', 'マネロン'],
        'judicial': ['刑事事件外'],
        'radius': ['国際'],
        'violence_eco': ['経済中心'],
    },
    'sihanoukville_china': {
        'economy': ['カジノ', 'IT詐欺'],
        'judicial': ['刑事事件外'],
        'radius': ['国際'],
        'violence_eco': ['経済中心'],
    },
    'drug_smuggling_routes': {
        'economy': ['薬物'],
        'judicial': ['確定済'],
        'radius': ['国際'],
        'violence_eco': ['経済中心'],
    },
    'drug_korea_route': {
        'economy': ['薬物'],
        'radius': ['国際'],
        'violence_eco': ['経済中心'],
    },
    'drug_china_southeast': {
        'economy': ['薬物'],
        'radius': ['国際'],
        'violence_eco': ['経済中心'],
    },
    'drug_meth_2019_yokohama': {
        'economy': ['薬物'],
        'judicial': ['確定済'],
        'radius': ['国際'],
        'violence_eco': ['経済中心'],
    },
    'shutoken_serial_2024': {
        'economy': ['IT詐欺'],
        'judicial': ['公判中'],
        'radius': ['広域'],
        'violence_eco': ['暴力中心'],
    },
    'pachinko_extortion_zone': {
        'economy': ['みかじめ料'],
        'judicial': ['確定済'],
        'radius': ['市内'],
        'violence_eco': ['暴力中心'],
    },
    'snack_kuyakushotsuki': {
        'economy': ['みかじめ料'],
        'judicial': ['確定済'],
        'radius': ['市内'],
        'violence_eco': ['暴力中心'],
    },
    'construction_extortion_kitakyushu': {
        'economy': ['建設業'],
        'judicial': ['確定済'],
        'radius': ['市内'],
        'violence_eco': ['暴力中心'],
    },
    'yawata_iron_works_area': {
        'economy': ['港湾労働'],
        'judicial': ['刑事事件外'],
        'radius': ['広域'],
        'violence_eco': ['市民・文化'],
    },
    'tanga_market': {
        'economy': ['闇市・露店'],
        'judicial': ['刑事事件外'],
        'radius': ['市内'],
        'violence_eco': ['市民・文化'],
    },
    'kokura_yamiichi_1946': {
        'economy': ['闇市・露店'],
        'judicial': ['刑事事件外'],
        'radius': ['市内'],
        'violence_eco': ['市民・文化'],
    },
    'kobe_yamaguchi_origin': {
        'economy': ['港湾労働'],
        'judicial': ['刑事事件外'],
        'radius': ['市内'],
        'violence_eco': ['経済中心'],
    },
}


def infer_tags(site):
    """site dict → {axis: [values]}"""
    slug = site['slug']
    kind = site['kind'] or ''
    faction = site['faction_tag'] or ''
    era = site['era_tag'] or ''
    notes = (site['notes'] or '').lower()
    label = (site['label'] or '').lower()

    tags = {'economy': [], 'judicial': [], 'radius': [], 'violence_eco': []}

    # violence_eco heuristics
    if kind == 'attack_site':
        tags['violence_eco'] = ['暴力中心']
    elif kind == 'ruling':
        tags['violence_eco'] = ['司法・行政']
    elif faction in ('司法側', '県警側'):
        tags['violence_eco'] = ['司法・行政']
    elif faction in ('市民側', '著作者'):
        tags['violence_eco'] = ['市民・文化']
    elif faction in ('トクリュウ', '半グレ'):
        tags['violence_eco'] = ['両方']
    elif faction in ('工藤組系', '田中組系', '草野一家系', '山口組系', '道仁会系',
                     '福博会系', '中国系'):
        if kind in ('hq_former', 'hq_current', 'lore_site'):
            tags['violence_eco'] = ['両方']
        else:
            tags['violence_eco'] = ['暴力中心']
    else:
        tags['violence_eco'] = ['市民・文化']

    # judicial heuristics
    if kind == 'attack_site':
        tags['judicial'] = ['確定済']
    elif kind == 'ruling':
        tags['judicial'] = ['確定済']
    elif faction in ('司法側', '県警側'):
        tags['judicial'] = ['行政処分のみ']
    elif faction in ('市民側', '著作者'):
        tags['judicial'] = ['刑事事件外']
    else:
        tags['judicial'] = ['行政処分のみ']

    # radius heuristics
    label_text = label + ' ' + notes
    if 'カンボジア' in label_text or 'フィリピン' in label_text or 'タイ' in label_text \
       or 'ベトナム' in label_text or 'ラオス' in label_text or '韓国' in label_text \
       or '香港' in label_text or 'ミャンマー' in label_text or '米国' in label_text \
       or 'イタリア' in label_text or 'マニラ' in label_text or 'バンコク' in label_text \
       or 'ホーチミン' in label_text or 'ハノイ' in label_text or 'プノンペン' in label_text \
       or 'ヴィエンチャン' in label_text or 'ヤンゴン' in label_text or 'シハヌークビル' in label_text:
        tags['radius'] = ['国際']
    elif '全国' in label_text or '全道' in label_text or '日本三大' in label_text \
       or '日本最大' in label_text or '日本初' in label_text:
        tags['radius'] = ['全国']
    elif '都道府県' in label_text or '広域' in label_text:
        tags['radius'] = ['広域']
    elif faction in ('工藤組系', '田中組系', '草野一家系') and '本部' in label_text:
        tags['radius'] = ['広域']
    elif faction in ('山口組系',) and ('本部' in label_text or '総本部' in label_text):
        tags['radius'] = ['全国']
    elif kind == 'district':
        tags['radius'] = ['町内']
    elif kind == 'attack_site':
        tags['radius'] = ['市内']
    else:
        tags['radius'] = ['市内']

    # economy heuristics
    if '薬物' in label_text or '覚せい剤' in label_text or 'ヒロポン' in label_text \
       or '大麻' in label_text or '危険ドラッグ' in label_text or 'ドラッグ' in label_text:
        tags['economy'].append('薬物')
    if 'みかじめ' in label_text or 'みかじめ料' in label_text:
        tags['economy'].append('みかじめ料')
    if '建設' in label_text or 'スクラップ' in label_text or '解体業' in label_text:
        tags['economy'].append('建設業')
    if '不動産' in label_text or '地上げ' in label_text or 'バブル' in label_text:
        tags['economy'].append('不動産・地上げ')
    if 'みずほ' in label_text or '銀行' in label_text or '金融' in label_text \
       or '反社融資' in label_text:
        tags['economy'].append('金融・銀行')
    if '詐欺' in label_text or '特殊詐欺' in label_text or 'ルフィ' in label_text \
       or 'トクリュウ' in label_text or 'SNS' in label_text or 'ロマンス' in label_text:
        tags['economy'].append('IT詐欺')
    if '芸能' in label_text or '神戸芸能' in label_text or '相撲' in label_text \
       or '八百長' in label_text or '黒い霧' in label_text:
        tags['economy'].append('興行・芸能')
    if '政治' in label_text or 'ロッキード' in label_text or '献金' in label_text \
       or '児玉誉士夫' in label_text:
        tags['economy'].append('政治献金')
    if 'マネロン' in label_text or 'マネー' in label_text or '仮想通貨' in label_text \
       or '900口座' in label_text:
        tags['economy'].append('マネロン')
    if '港湾' in label_text or '製鐵所' in label_text or 'ヤミ' in label_text:
        tags['economy'].append('港湾労働')
    if '闇市' in label_text or 'テキ屋' in label_text or '旦過' in label_text \
       or '魚町銀天街' in label_text or '商店街' in label_text:
        tags['economy'].append('闇市・露店')
    if 'カジノ' in label_text:
        tags['economy'].append('カジノ')

    # 何もマッチしなければ「資金源なし」
    if not tags['economy']:
        if faction in ('市民側', '著作者', '司法側', '県警側'):
            tags['economy'] = ['資金源なし']
        elif faction in ('工藤組系', '田中組系', '草野一家系', '山口組系',
                         '道仁会系', '福博会系'):
            tags['economy'] = ['みかじめ料']  # 暴力団系のデフォルト
        elif faction in ('トクリュウ', '半グレ'):
            tags['economy'] = ['IT詐欺']
        else:
            tags['economy'] = ['資金源なし']

    return tags


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # tag id lookup
    tag_lookup = {}  # (axis, value) → id
    for r in cur.execute('SELECT id, axis, value FROM tag').fetchall():
        tag_lookup[(r[1], r[2])] = r[0]

    # Clear existing site_tag
    cur.execute('DELETE FROM site_tag')

    sites = cur.execute(
        'SELECT id, slug, label, kind, faction_tag, era_tag, notes FROM site'
    ).fetchall()
    sites_dicts = [
        {'id': r[0], 'slug': r[1], 'label': r[2], 'kind': r[3],
         'faction_tag': r[4], 'era_tag': r[5], 'notes': r[6]}
        for r in sites]

    n_inserted = 0; explicit_used = 0
    for site in sites_dicts:
        if site['slug'] in EXPLICIT_TAGS:
            tags = EXPLICIT_TAGS[site['slug']]
            explicit_used += 1
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

    # 統計
    print(f'phase57_axis_backfill: +{n_inserted} site_tag rows')
    print(f'  explicit overrides used: {explicit_used}')
    print()
    for axis in ('economy', 'judicial', 'radius', 'violence_eco'):
        print(f'  {axis}:')
        rows = cur.execute(
            'SELECT t.value, COUNT(*) FROM site_tag st '
            'JOIN tag t ON st.tag_id = t.id '
            'WHERE t.axis = ? GROUP BY t.value ORDER BY 2 DESC',
            (axis,)).fetchall()
        for v, c in rows:
            print(f'    {v}: {c}')
    con.close()


if __name__ == '__main__':
    main()
