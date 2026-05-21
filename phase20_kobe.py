"""Phase 20: 神戸・山口組史 — 1915 創設から 2020 特定抗争指定まで。

カバー:
  - 1915 山口春吉 山口組創設(神戸港労働者監督)
  - 三代目山口組(1946-1984 / 田岡一雄)
  - 1984 田岡死去・分裂 → 1985 一和会創設
  - 山一抗争 1985-1989(全国規模)
  - 暴対法 1991(山一抗争の社会的影響)
  - 1989 五代目 山口組(渡辺芳則)
  - 2005 六代目 山口組(司忍)
  - 2015 神戸山口組 分裂
  - 2017 任侠山口組 分裂
  - 2020 絆會へ改称・特定抗争指定
  - 2023 段階的解除

Idempotent. Run: python phase20_kobe.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('kb_yamaguchi_1915', 'book', '山平重樹 / 山口組史',
     '山口春吉 山口組創設(1915)', None, '1915-'),
    ('kb_taoka', 'book', '溝口敦 / 田岡一雄評伝',
     '三代目 田岡一雄 関連書籍', None, '1946-1984'),
    ('kb_yamaichi_breakup', 'news', '読売新聞 / 朝日新聞',
     '1985 一和会創設報道', None, '1985-08-27'),
    ('kb_yamaichi_war', 'book', '山平重樹 / 朝日新聞',
     '山一抗争(1985-1989)関連書籍', None, '1985-1989'),
    ('kb_5daime', 'news', '朝日新聞',
     '五代目山口組 渡辺芳則 就任(1989)', None, '1989'),
    ('kb_6daime', 'news', '朝日新聞 / 共同通信',
     '六代目山口組 司忍 就任(2005-07)', None, '2005-07'),
    ('kb_kobeyamaguchi', 'news', '朝日新聞 / 共同通信',
     '神戸山口組 結成報道(2015-08-27)', None, '2015-08-27'),
    ('kb_ninkyo_split', 'news', '朝日新聞',
     '任侠山口組 分派(2017-04)', None, '2017-04'),
    ('kb_kizuna', 'news', '朝日新聞',
     '絆會 改称(2020-01)', None, '2020-01'),
    ('kb_tokutei_kousou_apply', 'official_release', '国家公安委員会',
     '六代目・神戸 特定抗争指定(2020-01-07)', 'https://www.npa.go.jp/', '2020-01-07'),
    ('kb_tokutei_kousou_release', 'official_release', '国家公安委員会',
     '特定抗争指定 段階的解除(2023-)', 'https://www.npa.go.jp/', '2023-08'),
    ('kb_hyogo_keisatsu', 'official_release', '兵庫県警察本部',
     '山口組関連 検挙状況', 'https://www.police.pref.hyogo.lg.jp/', '2010-2024'),
    ('kb_yamaguchi_kyushu', 'book', '報道書籍',
     '山口組 九州進出(1980s)関連', None, '1980s-'),
]


EVENTS = [
    ('kobe_yamaguchi_origin', 'kb_yamaguchi_1915',
     'merger', '1915',
     '山口春吉 山口組創設',
     '1915年、山口春吉が神戸港の労働者監督として山口組を結成。'
     '神戸港の港湾労働文化と地続きの組織として始まる。'
     '110年以上の歴史を持つ日本最古級のヤクザ系統の出発点。',
     None, None, None, '戦後闇市', '山口組系', 4),

    ('kobe_yamaguchi_souhonbu', 'kb_taoka',
     'lore', '1946-1984',
     '三代目 田岡一雄 — 全国組織への拡張',
     '田岡一雄(1946 就任)は全国組織化を推進。'
     '神戸を本拠に大阪・東京・名古屋へ系列を広げ、'
     '戦後ヤクザ史の中核人物となる。',
     None, None, None, '戦後闇市', '山口組系', 4),

    ('kobe_yamaichi_ground_zero', 'kb_yamaichi_breakup',
     'faction_split', '1985-08-27',
     '一和会 創設 — 三代目山口組分裂',
     '1985年8月27日、田岡死去後の組織継承をめぐる対立で、'
     '一部幹部が離脱して一和会を結成。山一抗争の起点。',
     None, None, None, '高度成長', '山口組系', 5),

    ('kobe_yamaichi_ground_zero', 'kb_yamaichi_war',
     'war', '1985-1989',
     '山一抗争 — 全国規模5年間',
     '1985-1989年、山口組と一和会の抗争「山一抗争」が全国規模で展開。'
     '約300件以上の襲撃事件が報じられ、一般市民巻き添えの懸念が社会問題化。'
     '後の暴対法(1991)成立の最大の社会的背景となった。',
     '組関係者・市民', '拳銃', '多数死傷', '高度成長', '山口組系', 5),

    ('kobe_yamaguchi_souhonbu', 'kb_5daime',
     'merger', '1989',
     '五代目 山口組 渡辺芳則 就任',
     '山一抗争終結とほぼ同時期、渡辺芳則が五代目組長に就任。'
     '抗争後の組織再編期を主導した。',
     None, None, None, '高度成長', '山口組系', 3),

    ('osaka_yamaguchi_kizunabashi', 'kb_yamaguchi_kyushu',
     'lore', '1980s',
     '山口組 九州進出と工藤會の防衛',
     '1980年代、山口組系列が大阪を中継地として九州進出を強化。'
     '北九州の地場連合体(工藤会・草野一家)が防衛姿勢を強め、'
     '1987年の工藤連合草野一家成立につながる地政学的圧力。',
     None, None, None, '高度成長', '山口組系', 4),

    ('kobe_yamaguchi_souhonbu', 'kb_6daime',
     'merger', '2005-07',
     '六代目 山口組 司忍 就任',
     '2005年7月、司忍が六代目組長に就任。'
     '工藤會の野村悟と同時代の組織トップとして、日本最大の指定暴力団を率いる。',
     None, None, None, '平成抗争', '山口組系', 3),

    ('kobe_kobeyamaguchigumi_hq', 'kb_kobeyamaguchi',
     'faction_split', '2015-08-27',
     '神戸山口組 結成 — 六代目山口組分裂',
     '2015年8月27日、六代目山口組から複数の二次団体が離脱して '
     '神戸山口組を結成。30年ぶりの山口組大規模分裂。',
     None, None, None, '頂上作戦', '山口組系', 5),

    ('kobe_kizunakai_hq', 'kb_ninkyo_split',
     'faction_split', '2017-04',
     '任侠山口組 分派',
     '神戸山口組から離脱した任侠山口組が結成。'
     '「六代目 vs 神戸 vs 任侠」の三派対立構図が確立。',
     None, None, None, '頂上作戦', '山口組系', 4),

    ('kobe_kizunakai_hq', 'kb_kizuna',
     'merger', '2020-01',
     '絆會 改称',
     '任侠山口組が組織名を「絆會(きずなかい)」に変更。'
     '「山口組」の名称を外し、新組織としての方針を打ち出す。',
     None, None, None, '解体後', '山口組系', 3),

    ('kobe_yamaguchi_souhonbu', 'kb_tokutei_kousou_apply',
     'designation', '2020-01-07',
     '六代目・神戸 特定抗争指定',
     '改正暴対法に基づき、六代目山口組と神戸山口組を「特定抗争指定暴力団」に指定。'
     '工藤會の特定危険指定とは別カテゴリだが、両組織への抗争圧力低減を目的とする。',
     None, None, None, '解体後', '司法側', 5),

    ('kobe_yamaguchi_souhonbu', 'kb_tokutei_kousou_release',
     'designation', '2023-08',
     '特定抗争指定 段階的解除',
     '抗争事件の沈静化を受け、六代目・神戸両組織の特定抗争指定が '
     '段階的に解除へ。一方、工藤會の特定危険指定は別判断で更新が継続。',
     None, None, None, '解体後', '司法側', 3),

    ('hyogo_keisatsu_hq', 'kb_hyogo_keisatsu',
     'lore', '2010-2024',
     '兵庫県警 — 三派対立の主軸',
     '兵庫県警は六代目・神戸・絆會の三派対立への対応を主導。'
     '頂上作戦と並走する形で、抗争鎮静化の捜査・規制を継続した。',
     None, None, None, '頂上作戦', '県警側', 3),

    ('shinobu_tsukasa_kobe', 'kb_6daime',
     'lore', '2005-',
     '司忍と野村悟 — 同時代の組織トップ',
     '六代目山口組組長 司忍と工藤會会長 野村悟は同時代の組織トップ。'
     '系統・縄張り・手口は大きく異なるが、'
     '平成期日本の指定暴力団トップの二人として、報道書籍で並列で語られる。',
     None, None, None, '平成抗争', '山口組系', 3),
]


LORE = [
    (1500, 'kobe_yamaichi_ground_zero', '1985-1989',
     '山一抗争 — 5年で300件',
     '山一抗争の5年間に報じられた襲撃事件は約300件以上。'
     '日本のヤクザ抗争史で最大規模・最長期間の一つ。'
     '一般市民が巻き添えで死傷する事案も発生し、暴対法成立の最重要背景となった。',
     5, '高度成長', '山口組系', 'kb_yamaichi_war'),

    (1510, 'kobe_yamaguchi_origin', '1915-',
     '神戸港から始まった山口組',
     '神戸港の労働者監督として始まった山口組は、110年以上の歴史を持つ。'
     '工藤會の戦後闇市出自(1947)とは異なり、明治末期からの '
     '港湾労働文化と地続きの組織。日本ヤクザ史の系統の多様性を示す。',
     4, '戦後闇市', '山口組系', 'kb_yamaguchi_1915'),

    (1520, 'kobe_yamaguchi_souhonbu', '1980s',
     '田岡一雄 vs 三代目総裁制',
     '田岡一雄時代の山口組は「全国組織化」を推進した一方、'
     '工藤會・草野一家は「九州地場連合体」として地域防衛に重点。'
     '同じ時代の異なる戦略が、両系統の現代の姿を分けた。',
     4, '高度成長', '山口組系', 'kb_taoka'),

    (1530, 'kobe_yamaichi_ground_zero', '1988',
     '一般市民の死亡事件 — 抗争の臨界点',
     '1988年、山一抗争中に一般市民の死亡事件が報じられた。'
     '社会的批判が決定的に高まり、政府・与党の暴対法立法化の最後の押し上げとなった。'
     '工藤會の市民襲撃4事件とは時代も系統も違うが、'
     '「市民の巻き添え」が司法を動かしたという構造は共通。',
     5, '高度成長', '山口組系', 'kb_yamaichi_war'),

    (1540, 'kobe_kobeyamaguchigumi_hq', '2015-08-27',
     '神戸山口組分裂 — 30年ぶりの大規模分裂',
     '1985年の山一抗争分裂から30年ぶりの山口組大規模分裂。'
     '当時の関係者が「歴史は繰り返す」と語る一方、'
     '暴対法時代の組織運営の困難が背景にある「経済的分裂」として分析される。',
     5, '頂上作戦', '山口組系', 'kb_kobeyamaguchi'),

    (1550, 'kobe_kizunakai_hq', '2020-01',
     '絆會 改称 — 「山口組」の名前を捨てる',
     '2020年、任侠山口組が絆會へ改称し「山口組」の名称を外した。'
     '「山口組」というブランドの規制対象性から距離を置く戦略。'
     '組織犯罪研究では「ブランド継承拒否」の象徴的事例として分析される。',
     4, '解体後', '山口組系', 'kb_kizuna'),

    (1560, 'osaka_yamaguchi_kizunabashi', '1985-2024',
     '関西 vs 九州 — 二つの組織犯罪文化',
     '関西の山口組系列と九州の地場連合体(工藤會・道仁会)は、'
     '組織構造・経済基盤・手口のすべてで対照的な系統。'
     'OSINT 比較研究で繰り返し論じられる二大文化圏。',
     4, '解体後', '山口組系', 'kb_yamaguchi_kyushu'),

    (1570, 'shinobu_tsukasa_kobe', '2005-',
     '司忍 — 服役と組織継続',
     '司忍は2005年の六代目就任後、別件で服役を経て2011年に出所。'
     '工藤會の野村悟が頂上作戦で2014年逮捕されたのとは対照的に、'
     '六代目山口組は組長服役中も組織形態を維持した。',
     3, '平成抗争', '山口組系', 'kb_6daime'),
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
    ev_inserted = 0; lr_inserted = 0; missing = set()
    for (slug, src_key, kind, date, title, summary, victim, weapon, resolution,
         era, faction, severity) in EVENTS:
        site_id = s_ids.get(slug)
        if site_id is None:
            missing.add(slug); continue
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
        if slug and site_id is None:
            missing.add(slug); continue
        src_id = src_ids.get(src_key) if src_key else None
        cur.execute('DELETE FROM lore WHERE COALESCE(site_id, 0)=COALESCE(?, 0) '
                    'AND COALESCE(year_label,"")=? AND title=?',
                    (site_id, year or '', title))
        cur.execute('INSERT INTO lore(ord, site_id, year_label, title, body, spice, '
                    ' era_tag, faction_tag, source_id) VALUES (?,?,?,?,?,?,?,?,?)',
                    (ord_, site_id, year, title, body, spice, era, faction, src_id))
        lr_inserted += 1
    con.commit()
    print(f'phase20_kobe: +{ev_inserted} events, +{lr_inserted} lore')
    if missing: print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
