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
    ('phase27_drug_tokuryu.py','薬物 + トクリュウ重点深掘り(ヒロポン戦後史・密輸ルート・ルフィ事件公判・SNSリクルーター・暗号資産マネロン・コンパウンド被害者保護)'),
    ('phase28_tokuryu_neighborhoods.py','トクリュウ・半グレ拠点に周辺情報補填(narration + life_snippet, 現地の空気感)'),
    ('phase29_specific_addresses.py','具体的住所・建物名・店舗名を notes に補強(被害者名は伏せたまま)'),
    ('phase30_persons_testimony_pros.py','人物・証言・訴訟を大幅拡充(persons 16→35, testimony 8→27, prosecutions 4→23)'),
    ('phase31_chronicle_orgs.py','chronicle 16→51, org_tree 16→43 に拡充'),
    ('phase33_url_completion.py','source の outlet 名から公式ホームページ URL を補完 → phase8 が og:image 取得可能に'),
    ('phase34_more_regions.py','北海道(札幌すすきの・函館・小樽)・東北(仙台国分町・福島連合)・四国(高松丸亀町・松山)・北陸(新潟古町・金沢片町)+ 震災復興と暴排'),
    ('phase35_kokura_facility.py','小倉(北九州市)各拠点の施設情報・解説段落を充実'),
    ('phase36_facility_nationwide.py','全国拠点(神戸・大阪・京都・名古屋・東京関東・広島・沖縄・北海道・東北・四国・北陸・久留米)の周辺施設情報を厚く補強'),
    ('phase37_atmosphere.py','narration の無かった重要拠点 56 ヶ所に臨場感ある解説段落を追加'),
    ('phase38_atmosphere2.py','残り 77 拠点 全てに narration 補完 — 227/227 (100%) カバー達成'),
    ('phase39_life_lore.py','life_snippet(街のいま)を 30→76 件に拡張 — 72 拠点で「今そこに立った風景」'),
    ('phase40_life_extend.py','life_snippet を 76→163 件に拡張 — 159/227 (70%) 拠点でカバー'),
    ('phase41_life_complete.py','life_snippet 残り 68 拠点を補完 — 227/227 (100%) 達成'),
    ('phase42_real_urls.py','主要事件の source.url を WebSearch 確認済の実 URL に置換(28件 story-specific URL 化)'),
    ('phase43_fact_corrections.py','WebSearch 検証で判明した主要事実の修正(本部解体 2019-07→2019-11-22, OFAC 2023-02-23→2013-02-15, 旦過市場火災規模数値)'),
    ('phase44_tokuryu_nationwide.py','トクリュウ全国分布拡充 — 25 新規拠点(2024-2025最新事案・全国分布・国際拠点)+ 多角的データ(34 narration + 25 life + 12 events + 22 sources 実 URL付)'),
    ('phase45_tokuryu_life_depth.py','phase44 25拠点の周辺生活情報深化 — 2-3枚目の life_snippet(街並み・時間帯・通行人・近隣ランドマーク・地域文化)'),
    ('phase46_local_media.py','各拠点に地元メディア・行政情報を関連付け(地方紙・テレビ・県/市役所・県警・暴追センター 31都道府県分)'),
    ('phase47_intl_media.py','海外拠点に国別の主要メディア・公的機関を追加(12 国・地域)'),
    ('phase48_city_media.py','都市・区レベルの地元メディア大幅追加(396 都市/区エントリ・tier 階層導入で都市レベルを上位表示)'),
    ('phase49_kokura_emotion.py','小倉・北九州拠点に「情感」追加(音・匂い・季節・時間帯・住民感情)'),
    ('phase50_strip_dialect.py','誤った北九州弁引用(博多弁・筑後弁の混入)を削除/修正'),
    ('phase51_neutralize_claims.py','地域固有性の過剰主張(○○特有の/世代記憶/うちの○○)を中立化'),
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
