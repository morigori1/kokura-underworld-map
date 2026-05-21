"""Phase 13: persons — publicly-named individuals tied to the Kudo-kai story.

Editorial policy (重要):
  - We include people whose names are PUBLIC, in one of these categories:
      (a) deceased historical figures (戦後初代総長など)
      (b) defendants in published court rulings (野村悟・田上不美夫)
      (c) authors of cited works (溝口敦・国正武重・Adelstein など)
      (d) academics with published Yakuza scholarship
  - We do NOT include current rank-and-file members, victims, or living
    individuals not already in the public record by their own work or by a
    court ruling.

Idempotent. Run: python phase13_persons.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('per_kusano_obit', 'news', '西日本新聞',
     '草野高明 関連 — 戦後ヤクザ史記述', None, '1990s-2000s'),
    ('per_kudo_obit', 'news', '西日本新聞 / 大分合同新聞',
     '工藤玄治 関連 — 中津・北九州ライン創設者の評伝', None, '1990s'),
    ('per_mizoshita_obit', 'news', '西日本新聞 / 共同通信',
     '溝下秀男 三代目総裁 死去報道', None, '2008-09-10'),
    ('per_nomura_court', 'ruling', '福岡地裁',
     '工藤會トップ判決 — 野村悟 被告', 'https://www.courts.go.jp/', '2021-08-24'),
    ('per_tanoue_court', 'ruling', '福岡地裁',
     '工藤會トップ判決 — 田上不美夫 被告', 'https://www.courts.go.jp/', '2021-08-24'),
    ('per_journalist_mizoguchi', 'book', '新潮社',
     '溝口敦 著者プロフィール', 'https://www.shinchosha.co.jp/', None),
    ('per_journalist_suzuki', 'book', '出版社プロフィール',
     '鈴木智彦 著者プロフィール', None, None),
    ('per_journalist_yamadira', 'book', '出版社プロフィール',
     '山平重樹 著者プロフィール', None, None),
    ('per_kitashiba', 'book', '出版社プロフィール',
     '北芝健 著者プロフィール', None, None),
    ('per_adelstein', 'book', 'Penguin / 講談社 ほか',
     'Jake Adelstein author bio', 'https://en.wikipedia.org/wiki/Jake_Adelstein', None),
    ('per_rankin', 'academic', 'Cambridge',
     'Andrew Rankin academic profile', None, None),
    ('per_okita_garyu', 'book', '出版社プロフィール',
     '沖田臥竜 著者プロフィール', None, None),
    ('per_kitano', 'film_ref', 'バンダイビジュアル ほか',
     '北野武 監督プロフィール(「アウトレイジ」)', None, None),
    ('per_fujii', 'film_ref', '映画製作会社',
     '藤井道人 監督プロフィール(「ヤクザと家族」)', None, None),
    ('per_yuzuki', 'book', '角川書店',
     '柚月裕子 著者プロフィール(「孤狼の血」原作)', None, None),
    ('per_kokkai', 'legislative_record', '衆議院',
     '暴対法改正審議の発言者プロフィール', 'https://kokkai.ndl.go.jp/', None),
    ('per_kunimasa', 'book', '出版社プロフィール',
     '国正武重 関連 — 頂上作戦ノンフィクション', None, None),
]


# slug, name, name_kana, role, faction_tag, born, died, site_slug, body, spice, source_key
PERSONS = [
    # ===== 戦後の祖 =====
    ('kusano_takaaki', '草野 高明', 'くさの たかあき',
     'founder', '草野一家系', '1920年代頃', '故人',
     'kusano_ikka_origin_kokura',
     '初代総長(草野一家)。戦後の小倉でテキ屋系から身を起こし、'
     '小倉駅・旦過市場周辺の闇市文化と地続きの「もうひとつの統治者」として '
     '報道書籍に繰り返し描かれてきた。生没年・出自の詳細は資料によって幅があるが、'
     '北九州ヤクザ史の出発点に位置する人物。',
     4, 'per_kusano_obit'),

    ('kudo_genji', '工藤 玄治', 'くどう げんじ',
     'founder', '工藤組系', '1920年代頃', '故人',
     'kudogumi_nakatsu_origin',
     '初代工藤組長。大分県中津市で1953年頃に工藤組を結成。'
     '関門海峡を跨ぐ「中津 — 門司 — 小倉」ラインを軸に勢力を伸ばし、'
     '後年の工藤連合草野一家成立(1987)の地理的基盤を作った。',
     3, 'per_kudo_obit'),

    ('mizoshita_hideo', '溝下 秀男', 'みぞした ひでお',
     'boss', '工藤會', '1941', '2008-09-10',
     'kudokai_hq_kandake',
     '工藤會 三代目総裁。2000年の工藤會改称後の組織形態整流の象徴的人物として '
     '報道された。2008年9月10日に病で死去。'
     '葬儀は工藤會本部周辺で行われ、福岡県警が大規模警備を展開したと報じられた。',
     4, 'per_mizoshita_obit'),

    # ===== 頂上作戦の被告(判決公開済み) =====
    ('nomura_satoru', '野村 悟', 'のむら さとる',
     'defendant', '工藤會', '1946', None,
     'kudokai_hq_kandake',
     '工藤會 五代目会長。2014年9月11日に頂上作戦で逮捕。'
     '2021-08-24 福岡地裁が市民襲撃4事件の首謀者として死刑判決。'
     '指定暴力団トップに死刑判決は史上初。判決言渡時の在廷発言「生涯後悔するぞ」が '
     '広く報じられた。2024-03-12 福岡高裁が死刑判決を破棄し無期懲役に減刑。',
     5, 'per_nomura_court'),

    ('tanoue_fumio', '田上 不美夫', 'たのうえ ふみお',
     'defendant', '工藤會', '1956', None,
     'kudokai_hq_kandake',
     '工藤會 理事長。2014年9月に頂上作戦で逮捕。'
     '2021-08-24 福岡地裁で野村と共謀の市民襲撃指示を認定され、無期懲役判決。'
     '2024-03-12 福岡高裁の控訴審で無期懲役を維持。',
     5, 'per_tanoue_court'),

    # ===== 著者・研究者 =====
    ('mizoguchi_atsushi', '溝口 敦', 'みぞぐち あつし',
     'author', '著作者', '1942', None, 'kudokai_hq_kandake',
     'ノンフィクション作家。新潮新書『暴力団』(2011)で工藤會を特定危険指定の典型として '
     '詳述。長年のヤクザ取材から「市民を直接標的にする」異常性をデータで論証し、'
     '2012年の特定危険指定制度新設の世論を後押しした側面がある。',
     4, 'per_journalist_mizoguchi'),

    ('suzuki_tomohiko', '鈴木 智彦', 'すずき ともひこ',
     'author', '著作者', '1966', None, 'kudokai_hq_kandake',
     'ジャーナリスト。『ヤクザときどき宇宙人』ほか、引退ヤクザのインタビューや '
     '組織犯罪の現場ルポを多数。工藤會傘下の元組員取材も含む。',
     3, 'per_journalist_suzuki'),

    ('yamadira_shigeki', '山平 重樹', 'やまだいら しげき',
     'author', '著作者', '1950', None, 'yamaguchigumi_kyushu_entry',
     'ノンフィクション作家。戦後ヤクザ史の系譜本を多数執筆。'
     '九州地場ヤクザの 1980年代抗争史や工藤連合草野一家成立の背景を扱う著作で '
     '研究者にも参照される。',
     3, 'per_journalist_yamadira'),

    ('kitashiba_ken', '北芝 健', 'きたしば けん',
     'author', '著作者', '1948', None, 'fukuoka_kenkei',
     '元警察関係者。退職後にヤクザ社会・組織犯罪に関する著作多数。'
     '工藤會を含む特定危険指定暴力団の取り扱いを実務目線で論じる。',
     3, 'per_kitashiba'),

    ('adelstein_jake', 'Jake Adelstein', None,
     'author', '著作者', '1969', None, 'kudokai_hq_kandake',
     'アメリカ人ジャーナリスト。読売新聞の記者として日本のヤクザ取材を続けたのち、'
     '『Tokyo Vice』(2009)で日本の指定暴力団を海外に紹介。'
     'HBO Max の同名ドラマ(2022-)でさらに国際的に広めた。',
     4, 'per_adelstein'),

    ('rankin_andrew', 'Andrew Rankin', None,
     'academic', '著作者', None, None, 'kudokai_hq_kandake',
     'ケンブリッジ大学関連のヤクザ研究者。'
     '日本の指定暴力団を国際比較組織犯罪研究の文脈に位置づける論考を執筆。'
     '工藤會は「日本で唯一市民を直接標的とする組織」として国際法学界で参照される。',
     3, 'per_rankin'),

    ('kunimasa_takeshige', '国正 武重(関連報道)', 'くにまさ たけしげ',
     'author', '著作者', None, None, 'fukuoka_kenkei',
     '報道書籍『工藤會壊滅作戦』関連の取材ライン。'
     '頂上作戦の捜査内側を県警側の動きから記述し、'
     '「直接証拠が出ない中で組織のトップを立てる」捜査方針の合理性を描く。',
     3, 'per_kunimasa'),

    # ===== 周辺カルチャー =====
    ('okita_garyu', '沖田 臥竜', 'おきた がりゅう',
     'author', '著作者', None, None, 'kudokai_hq_kandake',
     '作家・元組関係者と公言。ヤクザ社会内側からの語りを著作・SNS で発信。'
     '工藤會を含む特定危険指定の文脈にも言及があり、現役引退組員の発信層の代表。'
     '(取扱注意 — 個人発信、検証要。)',
     3, 'per_okita_garyu'),

    ('kitano_takeshi', '北野 武', 'きたの たけし',
     'film_maker', '著作者', '1947', None, 'kudokai_hq_kandake',
     '映画監督。「アウトレイジ」シリーズ(2010-2017)で暴対法時代のヤクザ抗争を映像化。'
     '直接 Kudo-kai を描くわけではないが、指定暴力団時代のヤクザ表象として '
     '海外も含めた文化的受容に大きな影響を与えた。',
     3, 'per_kitano'),

    ('fujii_michihito', '藤井 道人', 'ふじい みちひと',
     'film_maker', '著作者', '1986', None, 'kudokai_hq_kandake',
     '映画監督。「ヤクザと家族 The Family」(2021)で暴対法時代のヤクザ家族の '
     '経済的・社会的窒息を描く。'
     '工藤會頂上作戦と同時代の社会背景を共有する作品として並列参照される。',
     3, 'per_fujii'),

    ('yuzuki_yuko', '柚月 裕子', 'ゆづき ゆうこ',
     'author', '著作者', '1968', None, 'sakaimachi_quarter',
     '小説家。「孤狼の血」シリーズの原作者。'
     '広島の暴対法時代を舞台とする本シリーズは、'
     '北九州・工藤會研究と並列で語られる暴対法時代の文学の代表格。',
     3, 'per_yuzuki'),
]


# Org tree edges
ORG_TREE = [
    # child, parent, kind, started, ended, notes, faction_tag
    ('草野一家',          None,           'umbrella',     '1947',  '1987', '初代総長 草野高明、戦後小倉発祥', '草野一家系'),
    ('工藤組',            None,           'umbrella',     '1953',  '1987', '初代組長 工藤玄治、大分・中津発祥', '工藤組系'),
    ('工藤連合草野一家',  '草野一家',     'merged_into',  '1987',  '2000', '工藤組と草野一家の連合体', '工藤會'),
    ('工藤連合草野一家',  '工藤組',       'merged_into',  '1987',  '2000', '工藤組と草野一家の連合体', '工藤會'),
    ('工藤會',            '工藤連合草野一家', 'dissolved_into', '2000', None, '工藤連合草野一家を改称', '工藤會'),
    ('田中組',            '工藤會',       'direct_subord','2000',  '2019', '主要傘下組(報道による)', '田中組系'),
    ('極東組',            '工藤會',       'direct_subord','2000',  '2014', '主要傘下組(報道による)', '工藤會'),
    ('吉竹組',            '工藤會',       'direct_subord','2000',  '2014', '主要傘下組(報道による)', '工藤會'),
    # 全国コンテキスト
    ('六代目山口組',      None,           'umbrella',     '2005',  None,  '全国最大の指定暴力団', '山口組系'),
    ('神戸山口組',        '六代目山口組', 'offshoot_from','2015-08-27', None, '六代目山口組から分裂', '山口組系'),
    ('絆會(任侠山口組)', '神戸山口組',   'offshoot_from','2017-04', None,  '神戸山口組から離脱、後に絆會へ改称', '山口組系'),
    ('道仁会',            None,           'umbrella',     '1971',  None,  '久留米拠点の指定暴力団', '道仁会系'),
    ('九州誠道会',        '道仁会',       'offshoot_from','2006',  '2013', '道仁会から離脱、九州抗争の一方', '道仁会系'),
    ('浪川会',            '九州誠道会',   'dissolved_into','2013', None,  '九州誠道会の解散届を受けて再編', '道仁会系'),
    ('太州会',            None,           'umbrella',     '1978',  None,  '田川拠点の指定暴力団', '道仁会系'),
    ('福博会',            None,           'umbrella',     '1947',  None,  '福岡市拠点の指定暴力団', '福博会系'),
]


def upsert_sources(con) -> dict[str, int]:
    cur = con.cursor()
    keymap = {}
    for key, kind, outlet, title, url, pub in SOURCES:
        cur.execute(
            "DELETE FROM source WHERE outlet=? AND title=? AND COALESCE(published_on,'')=?",
            (outlet, title, pub or ''),
        )
        cur.execute(
            'INSERT INTO source(kind, outlet, title, url, published_on) '
            'VALUES (?,?,?,?,?)',
            (kind, outlet, title, url, pub),
        )
        keymap[key] = cur.lastrowid
    return keymap


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    s_ids = {row[0]: row[1] for row in cur.execute('SELECT slug, id FROM site')}
    src_ids = upsert_sources(con)

    cur.execute('DELETE FROM person')
    inserted = 0
    missing = []
    for (slug, name, kana, role, faction, born, died, site_slug, body, spice, src_key) in PERSONS:
        site_id = s_ids.get(site_slug) if site_slug else None
        if site_slug and site_id is None:
            missing.append(site_slug)
        src_id = src_ids.get(src_key) if src_key else None
        cur.execute(
            'INSERT INTO person(slug, name, name_kana, role, faction_tag, born, died, '
            ' site_id, body, spice, source_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (slug, name, kana, role, faction, born, died, site_id, body, spice, src_id),
        )
        inserted += 1

    cur.execute('DELETE FROM org_tree')
    for row in ORG_TREE:
        child, parent, kind, started, ended, notes, faction = row
        cur.execute(
            'INSERT INTO org_tree(child, parent, kind, started, ended, notes, faction_tag) '
            'VALUES (?,?,?,?,?,?,?)',
            (child, parent, kind, started, ended, notes, faction),
        )

    con.commit()
    print(f'phase13_persons: inserted {inserted} persons, {len(ORG_TREE)} org_tree edges')
    if missing:
        print(f'  WARN: missing slugs: {sorted(set(missing))}')
    con.close()


if __name__ == '__main__':
    main()
