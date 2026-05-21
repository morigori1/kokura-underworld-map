"""Phase 22: 広島・共政会 — 広島抗争・「仁義なき戦い」・「孤狼の血」。

カバー:
  - 1945-08-06 原爆投下 — 戦後広島の出発点(小倉との対比)
  - 1963 共政会創設 / 広島抗争 1963-1972
  - 1973-1974 深作欣二「仁義なき戦い」シリーズ
  - 1992 共政会 指定暴力団指定(暴対法施行第1陣)
  - 2015 柚月裕子「孤狼の血」原作 / 2018-2021 映画化
  - 「暴対法時代の地方都市と組織犯罪」の文学化

Idempotent. Run: python phase22_hiroshima.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('hr_genbaku', 'book', '広島市史 / 広島平和記念資料館',
     '原爆投下(1945-08-06)関連', None, '1945-08-06'),
    ('hr_kyoseikai_history', 'book', '報道書籍 / 中国新聞',
     '共政会史(1963-)関連', None, '1963-'),
    ('hr_hiroshima_war_1963', 'book', '深作欣二 / 飯干晃一 ほか',
     '広島抗争(1963-1972)関連', None, '1963-1972'),
    ('hr_jingi_movie', 'film_ref', '東映 / 深作欣二',
     '「仁義なき戦い」シリーズ(1973-1974)', None, '1973-1974'),
    ('hr_kyoseikai_designation', 'official_release', '広島県公安委員会',
     '共政会 指定暴力団指定(1992)', None, '1992'),
    ('hr_korou_no_chi_book', 'book', '柚月裕子 / 角川書店',
     '「孤狼の血」原作シリーズ', None, '2015-'),
    ('hr_korou_no_chi_movie', 'film_ref', '東映 / 白石和彌',
     '「孤狼の血」「LEVEL2」映画化', None, '2018-2021'),
    ('hr_chugoku_shinbun', 'news', '中国新聞',
     '広島ヤクザ史 連載報道', None, '1990s-'),
    ('hr_hiroshima_keisatsu', 'official_release', '広島県警察本部',
     '広島県警 暴力団対策統計',
     'https://www.pref.hiroshima.lg.jp/site/police/', '2010-2024'),
    ('hr_nagarekawa_culture', 'book', '広島街史 / 報道書籍',
     '流川 歓楽街文化', None, '1960s-'),
]


EVENTS = [
    ('hiroshima_atomic_park', 'hr_genbaku',
     'attack', '1945-08-06',
     '原爆投下(広島)— 戦後広島の出発点',
     '1945年8月6日、米軍が広島に原子爆弾を投下。'
     '中心市街地が壊滅し、戦後広島は瓦礫からの再出発となった。'
     '小倉(原爆代替標的)との対比で、北九州と広島の戦後史の二つの出発点。',
     '広島市民', '原子爆弾', '14万人以上死亡', '戦後闇市', '市民側', 5),

    ('hiroshima_kyoseikai_hq', 'hr_kyoseikai_history',
     'merger', '1963',
     '共政会 結成',
     '1963年、初代 山村辰雄が共政会を結成。'
     '広島市を本拠とする地場組織として発足、後の中国地方最大組織への道筋。',
     None, None, None, '高度成長', '司法側', 4),

    ('hiroshima_yakuza_war', 'hr_hiroshima_war_1963',
     'war', '1963-1972',
     '広島抗争 — 山口組進出 vs 地場組織',
     '1963-1972年、山口組系列の広島進出に対する地場組織(共政会・親和会等)の '
     '抗争。約9年にわたる断続的襲撃で、戦後広島の組織犯罪史の中核。'
     '深作映画「仁義なき戦い」の直接の素材。',
     '組関係者・市民', '拳銃・刃物', '多数死傷', '高度成長', '司法側', 5),

    ('hiroshima_jingi_movie', 'hr_jingi_movie',
     'lore', '1973-1974',
     '「仁義なき戦い」シリーズ — 5部作',
     '1973-1974年、東映・深作欣二監督による「仁義なき戦い」5部作が公開。'
     '飯干晃一の原作を基に広島抗争を描く。'
     '日本のヤクザ表象の原型を形成し、後の北野武「アウトレイジ」や '
     '柚月裕子「孤狼の血」の系譜の起点。',
     None, None, None, '高度成長', '著作者', 5),

    ('hiroshima_kyoseikai_designation', 'hr_kyoseikai_designation',
     'designation', '1992',
     '共政会 — 暴対法施行第1陣で指定暴力団に',
     '1992年の暴対法施行第1陣で、共政会は指定暴力団に。'
     '工藤連合草野一家(後の工藤會)と同時期の指定。'
     '広島ヤクザ史と九州ヤクザ史の規制史が並走する起点。',
     None, None, None, '高度成長', '司法側', 4),

    ('hiroshima_kyoseikai_offshoots', 'hr_chugoku_shinbun',
     'lore', '1960s-',
     '広島組系列 — 多系統並存',
     '共政会・浅野組・親和会・侠道会など、広島・中国地方の指定暴力団は '
     '複数系統が並存。工藤會の九州地場連合体的単一中心とは異なる構造。',
     None, None, None, '高度成長', '司法側', 3),

    ('hiroshima_nagarekawa', 'hr_nagarekawa_culture',
     'lore', '1960s-',
     '流川 — 広島ヤクザと歓楽街文化',
     '流川は広島市中心の歓楽街。共政会など広島地場組織と歓楽街文化が交わる中心地。'
     '小倉の堺町・久留米の文化街と並ぶ、地方主要都市の「組と歓楽街」の典型。',
     None, None, None, '高度成長', '司法側', 3),

    ('hiroshima_korou_no_chi', 'hr_korou_no_chi_book',
     'lore', '2015-',
     '柚月裕子「孤狼の血」原作シリーズ',
     '2015年、柚月裕子の小説「孤狼の血」が日本推理作家協会賞を受賞。'
     '広島ヤクザ史の系譜を、暴対法時代の刑事と組員の関係から描く。'
     '工藤會頂上作戦と同時代の文学的記録。',
     None, None, None, '頂上作戦', '著作者', 4),

    ('hiroshima_korou_no_chi', 'hr_korou_no_chi_movie',
     'lore', '2018-2021',
     '「孤狼の血」「LEVEL2」映画化',
     '白石和彌監督・役所広司主演で「孤狼の血」(2018)と「LEVEL2」(2021)が映画化。'
     '広島抗争の系譜を現代に蘇らせる作品として、'
     '北九州・工藤會研究と並列で語られる暴対法時代の文学・映像。',
     None, None, None, '頂上作戦', '著作者', 4),

    ('hiroshima_keisatsu', 'hr_hiroshima_keisatsu',
     'lore', '2010-2024',
     '広島県警 — 抗争史の蓄積',
     '広島県警は1963-1972 広島抗争への対応で蓄積された組織犯罪対策の経験を持つ。'
     '頂上作戦と並列で、地方警察の組織犯罪対応の代表事例として参照される。',
     None, None, None, '頂上作戦', '県警側', 3),
]


LORE = [
    (1900, 'hiroshima_atomic_park', '1945-08-06 / 1945-08-09',
     '広島と小倉 — 戦後の二つの出発点',
     '1945年8月6日に原爆投下を受けた広島と、'
     '8月9日に第二原爆の本来の標的だった小倉。'
     '二つの都市の戦後史は、原爆をめぐる対照的な経験から始まった。'
     '組織犯罪文化の発展も含めて、戦後の経路は両都市で大きく異なった。',
     5, '戦後闇市', '市民側', 'hr_genbaku'),

    (1910, 'hiroshima_yakuza_war', '1963-1972',
     '広島抗争 — 戦後ヤクザ抗争の原型',
     '広島抗争は、戦後日本の最大級のヤクザ抗争。'
     '都市部の組織間抗争が一般市民を巻き添えにする構図の原型。'
     '20年後の山一抗争・40年後の九州抗争に直接の影響を与えた、'
     '戦後組織犯罪史の重要な参照点。',
     5, '高度成長', '司法側', 'hr_hiroshima_war_1963'),

    (1920, 'hiroshima_jingi_movie', '1973-1974',
     '「仁義なき戦い」— 日本ヤクザ表象の原型',
     '深作欣二「仁義なき戦い」5部作は、日本のヤクザ映画の原型を形成。'
     '実録志向・暴力描写・組織内政治 — 後のすべてのヤクザ映画(北野武「アウトレイジ」 '
     '藤井道人「ヤクザと家族」「孤狼の血」)の祖となった作品。'
     '広島抗争の文学化は、後の工藤會表象の文化的背景でもある。',
     5, '高度成長', '著作者', 'hr_jingi_movie'),

    (1930, 'hiroshima_korou_no_chi', '2015-2021',
     '「孤狼の血」と頂上作戦の同時代性',
     '2015年「孤狼の血」原作・2018映画化・2021 LEVEL2 は、'
     '工藤會頂上作戦(2014)・一審判決(2021)とほぼ同時代に進行した。'
     '暴対法時代の地方都市と組織犯罪の物語が、'
     '北九州と広島の両方で同時並走的に文学化・映像化された稀有な期間。',
     4, '頂上作戦', '著作者', 'hr_korou_no_chi_movie'),

    (1940, 'hiroshima_nagarekawa', '1960s-2020s',
     '流川 vs 堺町 vs 文化街 — 地方都市の歓楽街と組',
     '広島の流川・小倉の堺町・久留米の文化街 — '
     '日本の地方主要都市の歓楽街と組織犯罪の関係は、'
     '各都市で異なる経路を辿りながら、似た構造を持っていた。'
     '頂上作戦・九州抗争・特定危険指定はすべて、'
     'この地方歓楽街文化の変容と並走している。',
     4, '頂上作戦', '司法側', 'hr_nagarekawa_culture'),

    (1950, 'hiroshima_kyoseikai_hq', '1963-2024',
     '共政会 60年史 — 工藤會との並行',
     '共政会は1963年結成、2024年現在60年以上の歴史。'
     '工藤会(1953)・草野一家(1947)と同世代の地場組織として、'
     '広島・北九州の両都市で並行する経路を辿った。'
     '頂上作戦のような首謀者責任追及は共政会に対しては行われていないが、'
     '組織形態の弱体化は同時代に進行している。',
     3, '解体後', '司法側', 'hr_kyoseikai_history'),
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
    print(f'phase22_hiroshima: +{ev_inserted} events, +{lr_inserted} lore')
    if missing: print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
