"""Phase 58: 国際接続線(site_link)— 拠点間の関係を線で結ぶ。

地図上に Leaflet polyline で描画する関係:
  - tokuryu_intl  : トクリュウ国内事件 → 海外指示拠点
  - sanction      : OFAC 制裁線(米国 → 工藤會など)
  - compound_route: メコン地域コンパウンド → 日本被害者保護事案
  - yamaguchigumi_split: 山口組分裂(本部 ↔ 神戸 ↔ 絆會)
  - origin        : 系譜(草野一家発祥 → 工藤會本部 等)
  - sister_proj   : 姉妹プロジェクト(本マップ ↔ Compound Time Machine)

各 link は(from_slug, to_slug, kind, note)で表現。
Idempotent: re-run で site_link を全消去 → 再生成。
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')
TODAY = '2026-05-25'
PROV = 'llm:claude-opus-4-7-1m'


LINKS = [
    # === ルフィ事件 — フィリピン Bicutan → 国内強盗 ===
    ('philippines_luffy_base', 'komae_robbery_2023', 'tokuryu_intl',
     'ルフィ事件指示(2023-01-19)'),
    ('philippines_luffy_base', 'kanagawa_yokohama_robbery', 'tokuryu_intl',
     'ルフィ指示 神奈川連続強盗'),
    ('philippines_luffy_base', 'chiba_isumi_robbery', 'tokuryu_intl',
     'ルフィ指示 千葉県内'),
    ('philippines_luffy_base', 'saitama_warabi_robbery', 'tokuryu_intl',
     'ルフィ指示 埼玉蕨'),
    ('philippines_luffy_base', 'ibaraki_chikusei_robbery', 'tokuryu_intl',
     'ルフィ指示 茨城筑西'),
    ('philippines_luffy_base', 'tochigi_oyama_robbery', 'tokuryu_intl',
     'ルフィ指示 栃木小山(致死)'),
    ('philippines_luffy_base', 'takasaki_gunma_robbery', 'tokuryu_intl',
     'ルフィ指示 群馬高崎'),
    ('philippines_luffy_base', 'kyoto_jewelry_robbery', 'tokuryu_intl',
     'ルフィ指示 京都貴金属店'),

    # === 指示役分散(ルフィ後)===
    ('philippines_luffy_base', 'thailand_tokuryu_base', 'split_after_takedown',
     'フィリピン摘発後 タイへ分散'),
    ('philippines_luffy_base', 'vietnam_tokuryu_base', 'split_after_takedown',
     'フィリピン摘発後 ベトナムへ分散'),
    ('philippines_luffy_base', 'laos_tokuryu_base', 'split_after_takedown',
     'フィリピン摘発後 ラオスへ分散'),
    ('philippines_luffy_base', 'cambodia_compounds_link', 'split_after_takedown',
     'フィリピン摘発後 カンボジアへ分散'),

    # === メコンコンパウンド → 日本人保護事案 ===
    ('myanmar_compounds_link', 'philippines_luffy_base', 'compound_route',
     'ミャンマー国境 ↔ マニラ(メコン地域犯罪ネットワーク)'),
    ('cambodia_compounds_link', 'philippines_luffy_base', 'compound_route',
     'カンボジア ↔ マニラ(地域横断ネットワーク)'),
    ('sihanoukville_china', 'cambodia_compounds_link', 'compound_route',
     'シハヌークビル 中国系投資 ↔ プノンペン コンパウンド'),
    ('myanmar_compounds_link', 'thailand_tokuryu_base', 'compound_route',
     'ミャンマー国境 KK Park ↔ タイ(国境を挟む)'),

    # === OFAC 制裁線 ===
    ('tokyo_us_embassy', 'kudokai_hq_kandake', 'sanction',
     'OFAC TCO 指定(2013-02-15)— 米国大使館経由で日本に伝達'),
    ('ofac_treasury_designation', 'kudokai_hq_kandake', 'sanction',
     'Treasury OFAC → 工藤會 TCO 指定'),
    ('intl_la_cosa_nostra_us', 'kudokai_hq_kandake', 'intl_comparison',
     'RICO 法のモデルとして工藤會頂上作戦と比較される'),

    # === 山口組分裂 ===
    ('kobe_yamaguchi_souhonbu', 'kobe_kobeyamaguchigumi_hq', 'split',
     '2015-08-27 神戸山口組分裂'),
    ('kobe_yamaguchi_souhonbu', 'kobe_kizunakai_hq', 'split',
     '2017-04 任侠山口組分派 → 2020-01 絆會'),
    ('kobe_kobeyamaguchigumi_hq', 'kobe_kizunakai_hq', 'split',
     '2017-04 神戸山口組から任侠山口組分派'),

    # === 系譜 ===
    ('kobe_yamaguchi_origin', 'kobe_yamaguchi_souhonbu', 'origin',
     '1915 神戸港創設 → 六代目山口組総本部(灘区)'),
    ('kusano_ikka_origin_kokura', 'kudokai_hq_kandake', 'origin',
     '1947 草野一家発祥 → 1987 工藤連合草野一家(本部 神岳)'),
    ('kudogumi_nakatsu_origin', 'kudokai_hq_kandake', 'origin',
     '1953 工藤組(中津)発祥 → 1987 工藤連合草野一家'),

    # === 九州抗争関係 ===
    ('kurume_dojinkai_main_hq', 'kurume_seidokai_hq', 'split',
     '2006 九州誠道会 道仁会から分派'),
    ('kurume_seidokai_hq', 'kurume_namikawakai_hq', 'origin',
     '2013 九州誠道会解散 → 浪川会再編'),

    # === 半グレ国際逃亡 ===
    ('roppongi_flower_attack', 'philippines_luffy_base', 'fugitive_intl',
     '見立真一(関東連合)2012-09-09 マニラへ逃亡(国際指名手配)'),

    # === Compound Time Machine 姉妹プロジェクト ===
    ('compound_time_machine_sister', 'myanmar_compounds_link', 'sister_proj',
     'メコンコンパウンドOSINT(姉妹プロジェクト)が詳述'),
    ('compound_time_machine_sister', 'cambodia_compounds_link', 'sister_proj',
     'メコンコンパウンドOSINT(姉妹プロジェクト)が詳述'),
    ('compound_time_machine_sister', 'sihanoukville_china', 'sister_proj',
     '中国系投資コンパウンドの衛星 OSINT'),

    # === 国際比較 ===
    ('intl_cosa_nostra_italy', 'kudokai_hq_kandake', 'intl_comparison',
     'シチリアマフィア研究との比較対象'),
    ('intl_ndrangheta_italy', 'kudokai_hq_kandake', 'intl_comparison',
     '\'ンドランゲタ研究との比較対象'),
    ('intl_triads_hk', 'doragon_chinese_hangure', 'intl_comparison',
     '香港 三合会 vs 江戸川区 怒羅権(中国系犯罪研究)'),
    ('intl_mekong_compounds_ref', 'cambodia_compounds_link', 'compound_route',
     'メコン詐欺コンパウンド研究の典型'),

    # === 韓国系密輸 ===
    ('busan_port', 'kobe_yamaguchi_origin', 'drug_route',
     '釜山 ↔ 神戸港(戦後密輸ルート)'),
    ('drug_korea_route', 'philippines_luffy_base', 'drug_route',
     '韓国系トクリュウ ↔ フィリピン拠点'),
    ('drug_china_southeast', 'sihanoukville_china', 'drug_route',
     '中国・東南アジアルート ↔ シハヌークビル'),

    # === 香港との接続 ===
    ('hk_mongkok', 'doragon_chinese_hangure', 'intl_comparison',
     '三合会(旺角)と中国系半グレ(江戸川区)の比較'),

    # === 銀行業界の反社遮断 ===
    ('mizuho_bank_hq', 'kudokai_hq_kandake', 'sanction',
     'みずほ業務改善命令(2013-09-27)→ 銀行業界の反社遮断強化'),
    ('zenginkyo_compliance', 'mizuho_bank_hq', 'origin',
     '全銀協 反社条項標準化 → みずほ事案で本格化'),

    # === 警察庁 トクリュウ対策 ===
    ('npa_tokuryu_analysis_room', 'philippines_luffy_base', 'sanction',
     '警察庁トクリュウ情報分析室(2025-10)— ルフィ事件以降の組織改編'),
    ('mpd_tokuryu_specialist', 'shutoken_serial_2024', 'sanction',
     '警視庁トクリュウ専従部門 → 首都圏連続強盗対応'),

    # === 阪神大震災と山口組炊き出し ===
    ('kansai_quake_yamaguchi', 'kobe_yamaguchi_souhonbu', 'origin',
     '阪神大震災当日(1995-01-17)— 五代目山口組本部前で炊き出し'),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    sites = {r[1]: r[0] for r in cur.execute('SELECT id, slug FROM site')}

    cur.execute('DELETE FROM site_link')
    n = 0; missing = []
    for from_slug, to_slug, kind, note in LINKS:
        fid = sites.get(from_slug)
        tid = sites.get(to_slug)
        if fid is None: missing.append(from_slug); continue
        if tid is None: missing.append(to_slug); continue
        cur.execute(
            'INSERT INTO site_link(from_site_id, to_site_id, kind, note, '
            ' created_by, created_at) VALUES (?,?,?,?,?,?)',
            (fid, tid, kind, note, PROV, TODAY))
        n += 1

    con.commit()
    print(f'phase58_intl_links: +{n} site_link rows')
    # Group by kind
    rows = cur.execute(
        'SELECT kind, COUNT(*) FROM site_link GROUP BY kind ORDER BY 2 DESC'
    ).fetchall()
    for k, c in rows:
        print(f'  {k}: {c}')
    if missing:
        print(f'  WARN: missing slugs: {sorted(set(missing))}')
    con.close()


if __name__ == '__main__':
    main()
