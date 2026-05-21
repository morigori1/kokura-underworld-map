"""Phase 21: 東京 — 住吉会・稲川会・反社規制の中枢・関東地場連合。

カバー:
  - 1949 稲川会創設 / 1958 住吉会(住吉一家から発展)
  - 関東地場連合の集中(住吉・稲川・極東・松葉・国粋)
  - 暴対法・改正暴対法の立法地
  - 警察庁・金融庁・米国大使館 — 規制と国際協調の主体
  - 半グレ・準暴力団(2013 警察庁概念創設)
  - 「龍が如く」「Tokyo Vice」の表象的中心地

Idempotent. Run: python phase21_tokyo.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('tk_inagawa_history', 'book', '溝口敦 / 山平重樹',
     '稲川会史(1949-)関連書籍', None, '1949-'),
    ('tk_sumiyoshi_history', 'book', '報道書籍',
     '住吉会史(1958-)関連書籍', None, '1958-'),
    ('tk_kabukicho_book', 'book', '報道書籍 / Jake Adelstein',
     '歌舞伎町 ヤクザ史関連', None, '1990s-'),
    ('tk_shibuya_pseudo_yakuza', 'official_release', '警察庁',
     '準暴力団 概念創設(2013)', 'https://www.npa.go.jp/', '2013'),
    ('tk_npa_white_each', 'police_whitepaper', '警察庁',
     '警察白書 — 関東情勢年次',
     'https://www.npa.go.jp/hakusyo/', '2010-2024'),
    ('tk_diet_bouhou', 'legislative_record', '衆参法務委員会',
     '暴対法 成立・改正審議録', 'https://kokkai.ndl.go.jp/', '1991-2024'),
    ('tk_fsa_action', 'official_release', '金融庁',
     '銀行業界 反社対応 行政処分', 'https://www.fsa.go.jp/', '2013-'),
    ('tk_us_embassy_ofac', 'foreign_press', 'Reuters / 朝日新聞',
     'OFAC 工藤會 TCO 指定 日米調整報道(2013)', None, '2013-02'),
    ('tk_npa_kanto', 'official_release', '警視庁',
     '関東主要組織 検挙状況', 'https://www.keishicho.metro.tokyo.lg.jp/', '2010-2024'),
    ('tk_tokyo_vice_show2', 'film_ref', 'HBO Max / WOWOW',
     '「Tokyo Vice」ドラマ — 歌舞伎町ヤクザ表象',
     'https://en.wikipedia.org/wiki/Tokyo_Vice_(TV_series)', '2022-'),
    ('tk_ryugagotoku_show', 'film_ref', 'セガ / Amazon Prime',
     '「龍が如く」シリーズ・ドラマ化 — 神室町表象', None, '2005-'),
]


EVENTS = [
    ('tokyo_inagawakai_hq', 'tk_inagawa_history',
     'merger', '1949',
     '稲川会 創設',
     '1949年、稲川聖城が稲川会を結成。神奈川・東京を中心に勢力を拡張。'
     '関東の地場ヤクザの主要組織の一つとして戦後発展した。',
     None, None, None, '戦後闇市', '司法側', 3),

    ('tokyo_sumiyoshi_hq', 'tk_sumiyoshi_history',
     'merger', '1958',
     '住吉会 結成',
     '1958年、住吉一家から発展して住吉会が成立。'
     '東京・関東を本拠とし、山口組と並ぶ全国2強の片翼として確立。',
     None, None, None, '戦後闇市', '司法側', 3),

    ('tokyo_diet_again', 'tk_diet_bouhou',
     'designation', '1991-05-15',
     '暴対法 成立(衆参法務委員会)',
     '東京・永田町の国会で「暴力団員による不当な行為の防止等に関する法律」 '
     '(暴対法)が成立。山一抗争(1985-1989)の社会的影響を直接の背景に持つ。'
     '工藤連合草野一家を含む全国主要組織が翌1992年から指定暴力団となる枠組み。',
     None, None, None, '高度成長', '司法側', 5),

    ('tokyo_diet_again', 'tk_diet_bouhou',
     'designation', '2012-10-30',
     '改正暴対法 — 特定危険指定創設',
     '2012年、改正暴対法が成立し「特定危険指定暴力団」「特定抗争指定暴力団」 '
     '制度が新設。工藤會を全国第1号として指定する直接の法的根拠。',
     None, None, None, '平成抗争', '司法側', 5),

    ('tokyo_npa_hq', 'tk_npa_white_each',
     'lore', '2010-2024',
     '警察庁 — 全国情勢の集約',
     '警察庁は全国の指定暴力団情勢を集約し、警察白書を毎年公表。'
     '工藤會頂上作戦の捜査方針の方向付け、'
     '2012年特定危険指定の運用設計の主体。',
     None, None, None, '頂上作戦', '県警側', 3),

    ('tokyo_fsa', 'tk_fsa_action',
     'designation', '2014',
     '金融庁 — みずほ銀行 業務改善命令',
     '2014年、金融庁がみずほ銀行に業務改善命令(反社融資問題)。'
     '銀行業界全体の反社チェック体制が一斉に厳格化、'
     '指定暴力団との金融遮断が決定的になった。',
     None, None, None, '平成抗争', '司法側', 4),

    ('tokyo_fsa', 'tk_fsa_action',
     'designation', '2018-',
     '金融庁 — 暗号資産取引所 反社対応強化',
     '2018年以降、金融庁が暗号資産交換業者の反社対応・AML を厳格化。'
     '工藤會を含む指定暴力団関係者の新興金融への接続を遮断。',
     None, None, None, '解体後', '司法側', 3),

    ('tokyo_us_embassy', 'tk_us_embassy_ofac',
     'sanctions', '2013-02-23',
     '米国大使館経由の OFAC TCO 指定調整',
     '2013-02-23 の OFAC 工藤會 TCO 指定は、東京の米国大使館を窓口とする '
     '日米当局間の事前協議を経て発表されたと報じられた。'
     '日本のヤクザに対する初めての金融制裁の起点。',
     None, None, None, '平成抗争', '司法側', 4),

    ('tokyo_kabukicho', 'tk_kabukicho_book',
     'lore', '1990s-',
     '歌舞伎町 — 関東ヤクザ表象の中心地',
     '新宿歌舞伎町は住吉会・稲川会・極東会など複数組織の縄張りが交錯。'
     '日本最大級の歓楽街として、組織犯罪報道の中心地でもあった。',
     None, None, None, '高度成長', '司法側', 3),

    ('tokyo_kabukicho', 'tk_tokyo_vice_show2',
     'lore', '2022-',
     '「Tokyo Vice」ドラマ — 歌舞伎町の表象',
     'HBO Max ドラマ「Tokyo Vice」は歌舞伎町を主舞台にする。'
     'Jake Adelstein の原作と並んで、日本のヤクザ文化を海外に広めた中核作品。',
     None, None, None, '解体後', '著作者', 3),

    ('tokyo_kabukicho', 'tk_ryugagotoku_show',
     'lore', '2005-',
     '「龍が如く」神室町 — 歌舞伎町モデル',
     'セガ「龍が如く」シリーズの架空の「神室町」は歌舞伎町をモデルにする。'
     '2025年のドラマ化(Amazon Prime)も含めて、'
     'カルチャーシーンでの日本のヤクザ表象の中核。',
     None, None, None, '解体後', '著作者', 3),

    ('tokyo_shibuya_yakuza', 'tk_shibuya_pseudo_yakuza',
     'designation', '2013',
     '警察庁 — 準暴力団 概念創設',
     '2013年、警察庁が「準暴力団」概念を創設。'
     '半グレ集団など、従来の指定暴力団系列とは異なる現代型組織犯罪を捕捉。'
     '工藤會のような伝統的指定暴力団とは別系統の組織犯罪対応の起点。',
     None, None, None, '平成抗争', '司法側', 4),

    ('tokyo_yakuzas_hubs', 'tk_npa_kanto',
     'lore', '2010-2024',
     '関東主要組織 — 5組織の並存',
     '東京・関東には住吉会・稲川会・極東会・松葉会・国粋会の '
     '5つの主要指定暴力団が並存。'
     '工藤會のような単一中心の九州地場連合体とは大きく異なる構造。',
     None, None, None, '高度成長', '司法側', 3),

    ('tokyo_metro_keisatsu', 'tk_npa_kanto',
     'lore', '2010-2024',
     '警視庁 — 関東主要組織への日常対応',
     '警視庁は関東主要5組織への日常対応の主軸。'
     '工藤會のような単発的市民威迫事案は管轄組織には少なく、'
     '主に組織間の抗争・経済犯罪対応が中心。',
     None, None, None, '頂上作戦', '県警側', 3),
]


LORE = [
    (1700, 'tokyo_diet_again', '1991-05-15',
     '暴対法成立の日 — 衆議院本会議',
     '1991年5月15日、衆議院本会議で暴対法が可決成立。'
     '当時の国会議事録には、山一抗争での一般市民死亡事件への言及が多数残る。'
     '工藤會のような市民威迫が問題化する20年以上前から、'
     '組織犯罪の市民への波及は立法の主要テーマだった。',
     5, '高度成長', '司法側', 'tk_diet_bouhou'),

    (1710, 'tokyo_us_embassy', '2013-02-23',
     'OFAC TCO 指定 — オバマ政権の判断',
     '米財務省 OFAC が工藤會を「特定国際犯罪組織」として制裁指定した日。'
     '東京の米国大使館を窓口とする日米調整は、報道書籍では「日本側の '
     '一部に驚きが広がった」と描く。'
     '日本のヤクザに対する初の金融制裁の歴史的瞬間。',
     5, '平成抗争', '司法側', 'tk_us_embassy_ofac'),

    (1720, 'tokyo_fsa', '2013-2014',
     'みずほ事件 — 銀行界の革命',
     '2013-2014のみずほ銀行反社融資問題は、日本の銀行業界の反社対応の '
     '「やる気のあるところからやる」段階を終わらせた事件。'
     '工藤會を含む指定暴力団の金融遮断が決定的になった、銀行業界史の節目。',
     5, '平成抗争', '司法側', 'tk_fsa_action'),

    (1730, 'tokyo_kabukicho', '1980s-2020s',
     '歌舞伎町 vs 堺町 — 二つの歓楽街文化',
     '東京の歌舞伎町と小倉の堺町は、ヤクザと歓楽街の関係の異なる二つの典型。'
     '歌舞伎町は複数組織が縄張りを共有、堺町は工藤會傘下の単一支配。'
     '組織構造の違いが街の文化に直接反映される事例。',
     4, '高度成長', '司法側', 'tk_kabukicho_book'),

    (1740, 'tokyo_shibuya_yakuza', '2013-',
     '渋谷 — 半グレと新しい組織犯罪',
     '渋谷を中心とする2000年代以降の半グレ集団は、'
     '伝統的指定暴力団系列とは別系統の現代型組織犯罪。'
     '警察庁「準暴力団」概念創設(2013)の直接の対象。'
     '工藤會のような伝統的ヤクザの弱体化と並走する形で、'
     '組織犯罪の主体が変化している現代の状況を示す。',
     4, '解体後', '司法側', 'tk_shibuya_pseudo_yakuza'),

    (1750, 'tokyo_yakuzas_hubs', '1985-',
     '関東5組織 vs 工藤會 — 構造比較',
     '関東の住吉・稲川・極東・松葉・国粋の5組織は、'
     '一極集中せず並存する分散型構造。'
     '一方の工藤會は北九州の単一中心型。'
     '同じ「指定暴力団」というラベルが、地域によって全く異なる組織構造を '
     '含むことを示す対比。',
     4, '高度成長', '司法側', 'tk_npa_kanto'),

    (1760, 'tokyo_npa_hq', '1991-2024',
     '警察庁 — 30年の組織犯罪対策の蓄積',
     '警察庁は暴対法成立(1991)から30年以上、'
     '指定暴力団・特定危険指定・特定抗争指定・準暴力団など、'
     '組織犯罪規制の枠組みを段階的に整備。'
     '工藤會頂上作戦はこの30年の蓄積の集大成的事案として位置づけ。',
     4, '解体後', '県警側', 'tk_npa_white_each'),
]


def upsert_sources(con) -> dict[str, int]:
    cur = con.cursor()
    keymap = {}
    for key, kind, outlet, title, url, pub in SOURCES:
        cur.execute(
            "DELETE FROM source WHERE outlet=? AND title=? AND COALESCE(published_on,'')=?",
            (outlet, title, pub or ''))
        cur.execute('INSERT INTO source(kind, outlet, title, url, published_on) VALUES (?,?,?,?,?)',
                    (kind, outlet, title, url, pub))
        keymap[key] = cur.lastrowid
    return keymap


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    s_ids = {row[0]: row[1] for row in cur.execute('SELECT slug, id FROM site')}
    src_ids = upsert_sources(con)
    ev_inserted = 0; lr_inserted = 0; missing = set()
    for (slug, src_key, kind, date, title, summary, victim, weapon, resolution,
         era, faction, severity) in EVENTS:
        site_id = s_ids.get(slug)
        if site_id is None: missing.add(slug); continue
        src_id = src_ids.get(src_key)
        cur.execute('DELETE FROM event WHERE site_id=? AND COALESCE(happened_on,"")=? AND title=?',
                    (site_id, date or '', title))
        cur.execute('INSERT INTO event(kind, happened_on, site_id, title, summary, '
                    ' victim_role, weapon, resolution, source_id, era_tag, faction_tag, severity) '
                    ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (kind, date, site_id, title, summary, victim, weapon, resolution,
                     src_id, era, faction, severity))
        ev_inserted += 1
    for (ord_, slug, year, title, body, spice, era, faction, src_key) in LORE:
        site_id = s_ids.get(slug) if slug else None
        if slug and site_id is None: missing.add(slug); continue
        src_id = src_ids.get(src_key) if src_key else None
        cur.execute('DELETE FROM lore WHERE COALESCE(site_id, 0)=COALESCE(?, 0) '
                    'AND COALESCE(year_label,"")=? AND title=?',
                    (site_id, year or '', title))
        cur.execute('INSERT INTO lore(ord, site_id, year_label, title, body, spice, '
                    ' era_tag, faction_tag, source_id) VALUES (?,?,?,?,?,?,?,?,?)',
                    (ord_, site_id, year, title, body, spice, era, faction, src_id))
        lr_inserted += 1
    con.commit()
    print(f'phase21_tokyo: +{ev_inserted} events, +{lr_inserted} lore')
    if missing: print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
