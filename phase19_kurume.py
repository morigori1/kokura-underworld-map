"""Phase 19: 久留米地域 — 道仁会・浪川会・九州抗争(2006-2013)詳細化。

工藤會マップから九州地場ヤクザ史マップへ。九州抗争は工藤會本部解体・
頂上作戦と並走する平成期九州犯罪史の南端の主要事件。

カバー:
  - 1971 道仁会結成 / 2006 分派 → 九州誠道会 / 2013 解散 → 浪川会再編
  - 文化街・西鉄久留米駅・甘木・荒尾の地理的拡散
  - 抗争期の市民生活への影響
  - 道仁会と工藤會の関係(直接対立はないが地場連合の比較対象)
  - 関連報道書籍

Idempotent. Run: python phase19_kurume.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('ku_dojin_founding', 'book', '報道書籍 / 西日本新聞',
     '道仁会 結成(1971)関連', None, '1971-'),
    ('ku_seidokai_breakup', 'news', '西日本新聞 / 共同通信',
     '九州誠道会 分派(2006)関連報道', None, '2006'),
    ('ku_war_2006', 'news', '西日本新聞 / 産経新聞',
     '九州抗争 — 初期発砲事件報道(2006-2008)', None, '2006-2008'),
    ('ku_war_peak', 'news', '西日本新聞 / 朝日新聞',
     '九州抗争 ピーク — 一般市民巻き添え事案(2010-2012)', None, '2010-2012'),
    ('ku_war_designation', 'official_release', '国家公安委員会',
     '道仁会・九州誠道会 特定抗争指定(2012-12-27)', 'https://www.npa.go.jp/', '2012-12-27'),
    ('ku_seidokai_disband', 'news', '西日本新聞',
     '九州誠道会 解散届提出(2013)', None, '2013-06'),
    ('ku_namikawakai_form', 'news', '西日本新聞',
     '浪川会 結成(2013)', None, '2013-07'),
    ('ku_bunkagai_serial', 'news', '西日本新聞 久留米支局',
     '文化街 連載 — 抗争前後の街の変化', None, '2008-2014'),
    ('ku_kumamoto_periphery', 'news', '熊本日日新聞',
     '熊本県内への抗争波及報道', None, '2008-2013'),
    ('ku_saga_periphery', 'news', '佐賀新聞',
     '佐賀県内への抗争波及報道', None, '2007-2012'),
    ('ku_amagi_attack', 'news', '西日本新聞 朝倉支局',
     '朝倉・甘木 関連事件報道', None, '2009-2012'),
    ('ku_book_dojinkai', 'book', '溝口敦 / 山平重樹 ほか',
     '道仁会・九州抗争 関連書籍', None, '2010s-'),
    ('ku_takara_dais', 'news', '西日本新聞',
     '高良大社 例祭と抗争期の街', None, '2010s'),
    ('ku_post_2013', 'news', '西日本新聞',
     '九州抗争後 — 文化街の回復連載', None, '2014-2020'),
    ('ku_kudokai_compare', 'book', '報道書籍',
     '工藤會 vs 道仁会 — 「市民を直接標的にする」異常性の比較', None, '2010s'),
    ('ku_namikawakai_split', 'news', '西日本新聞',
     '浪川会 内部動揺報道', None, '2014-2020'),
]


EVENTS = [
    ('kurume_dojinkai_main_hq', 'ku_dojin_founding',
     'merger', '1971',
     '道仁会 結成',
     '1971年、久留米市内で道仁会が結成。九州地場ヤクザの中核組織として、'
     '久留米を本拠に勢力を拡張。後の九州抗争の起点となる組織。',
     None, None, None, '高度成長', '道仁会系', 4),

    ('kurume_seidokai_hq', 'ku_seidokai_breakup',
     'faction_split', '2006',
     '九州誠道会 分派',
     '2006年、道仁会内の対立が表面化し、一部幹部が離脱して九州誠道会を結成。'
     '6年に及ぶ「九州抗争」の起点となった分裂。',
     None, None, None, '平成抗争', '道仁会系', 5),

    ('kurume_bunkagai_central', 'ku_war_2006',
     'attack', '2006-2008',
     '文化街 — 抗争初期の発砲',
     '2006-2008年、文化街周辺で道仁会・九州誠道会関連の発砲事件が連続。'
     '一般市民巻き添えの懸念から久留米市民の不安が広がる。',
     '組関係者', '拳銃', '複数死傷', '平成抗争', '道仁会系', 4),

    ('kurume_bunkagai_central', 'ku_war_peak',
     'attack', '2010-2012',
     '文化街 — 抗争ピーク期',
     '2010-2012年、九州抗争はピーク期。文化街・甘木方面で発砲事件が頻発。'
     '福岡県警の特別警戒態勢が長期化し、市内の暴排運動が急速に進展。',
     '組関係者', '拳銃', '複数死傷', '平成抗争', '道仁会系', 5),

    ('amagi_periphery', 'ku_amagi_attack',
     'attack', '2009-2012',
     '朝倉・甘木地区 関連事件',
     '朝倉市甘木地区でも九州抗争関連の事件が複数報じられた。'
     '久留米の北、北九州方面への動線上で抗争の地理的拡散が確認された。',
     '組関係者', '拳銃', '負傷', '平成抗争', '道仁会系', 3),

    ('arao_omuta', 'ku_kumamoto_periphery',
     'attack', '2008-2013',
     '熊本側(荒尾・大牟田)波及',
     '熊本県荒尾市・福岡県大牟田市の県境エリアで関連事件が報じられた。'
     '九州抗争の南端の地理的広がり。',
     '組関係者', '拳銃', '負傷', '平成抗争', '道仁会系', 3),

    ('saga_periphery_kyushu_war', 'ku_saga_periphery',
     'attack', '2007-2012',
     '佐賀県側 関連事件',
     '佐賀県内でも九州抗争関連の発砲事件が報じられた。'
     '九州中部から西部への地理的伝播を示す。',
     '組関係者', '拳銃', '負傷', '平成抗争', '道仁会系', 3),

    ('kurume_dojinkai_main_hq', 'ku_war_designation',
     'designation', '2012-12-27',
     '道仁会・九州誠道会 特定抗争指定',
     '改正暴対法に基づき、工藤會の特定危険指定と同時期、'
     '道仁会と九州誠道会を「特定抗争指定暴力団」に指定。'
     '事務所使用制限・暴排警戒区域の設定により抗争鎮静化を促した。',
     None, None, None, '平成抗争', '司法側', 5),

    ('kurume_seidokai_hq', 'ku_seidokai_disband',
     'dissolution', '2013-06',
     '九州誠道会 解散届提出',
     '2013年6月、九州誠道会が解散届を提出。'
     '長期抗争の継続困難と特定抗争指定の規制下で組織継続を断念。'
     '本部は売却・撤去された。',
     None, None, None, '平成抗争', '道仁会系', 4),

    ('kurume_namikawakai_hq', 'ku_namikawakai_form',
     'merger', '2013-07',
     '浪川会 結成',
     '九州誠道会解散後、組織形態を維持するため浪川会として再編。'
     '指定暴力団としての登録は継続。抗争の事実上の終結。',
     None, None, None, '平成抗争', '道仁会系', 4),

    ('kurume_namikawakai_hq', 'ku_namikawakai_split',
     'faction_split', '2014-2020',
     '浪川会 内部動揺',
     '結成後の浪川会内でも組員離脱・小規模分裂の報道が継続。'
     '九州抗争の余波が長期に残る構図。',
     None, None, None, '解体後', '道仁会系', 2),

    ('kurume_bunkagai_central', 'ku_post_2013',
     'lore', '2014-2020',
     '文化街 — 回復への歩み',
     '2013年の抗争終結後、文化街の店舗営業は段階的に回復。'
     '常連客の戻り、新規店舗の出店、地元客の帰還が地元紙連載に記録された。',
     None, None, None, '解体後', '市民側', 3),

    ('kurume_keisatsu', 'ku_war_peak',
     'lore', '2006-2013',
     '久留米警察 — 6年間の特別警戒',
     '九州抗争中、福岡県警久留米地区は特別警戒態勢を継続。'
     '抗争組織の事務所周辺・主要交差点での24時間警戒が常態化した。',
     None, None, None, '平成抗争', '県警側', 3),

    ('kurume_jr_station', 'ku_war_peak',
     'lore', '2010s',
     'JR 久留米駅 — 玄関口の緊張',
     '九州抗争中、JR 久留米駅の出入りも警察の警戒対象。'
     '新幹線停車駅としての玄関口性が、抗争組織の人員出入りの監視ラインになった。',
     None, None, None, '平成抗争', '県警側', 2),

    ('kurume_shrine_temple', 'ku_takara_dais',
     'lore', '2010s',
     '高良大社 — 祭りの日常と街の異常',
     '九州抗争期も高良大社の初詣・例祭は通常開催。'
     '「祭りの日常」が抗争期の「街の異常」と対比される地元紙コラム。',
     None, None, None, '平成抗争', '市民側', 3),

    ('kurume_west_arcade',  'ku_bunkagai_serial',
     'lore', '2010s',
     '西鉄久留米駅周辺 — 動線中心の不安',
     '西鉄久留米駅周辺の商業エリアでも、抗争期は巻き添えへの '
     '不安が市民に広がった。買い物客の足が遠のく時期があったと '
     '地元紙連載は記録する。',
     None, None, None, '平成抗争', '市民側', 2),

    # 工藤會との並列文脈
    ('kurume_dojinkai_main_hq', 'ku_kudokai_compare',
     'lore', '2010s',
     '工藤會 vs 道仁会 — 市民威迫の有無',
     '工藤會と道仁会・浪川会は両方とも九州地場の指定暴力団だが、'
     '工藤會が市民を直接の標的にしたのに対し、道仁会系の抗争は組織間に '
     '限定された。両者の比較は組織犯罪研究で繰り返し論じられる。',
     None, None, None, '平成抗争', '道仁会系', 3),
]


LORE = [
    (1300, 'kurume_seidokai_hq', '2006',
     '九州誠道会分派の引き金',
     '2006年の九州誠道会分派は、道仁会内の世代間対立・資金配分問題が '
     '直接の引き金とされる。報道書籍は「組織内の世代交代の失敗が外部抗争に転化した」 '
     '構図として描く。',
     4, '平成抗争', '道仁会系', 'ku_book_dojinkai'),

    (1310, 'kurume_bunkagai_central', '2006-2013',
     '文化街 — 6年間の「夜の静けさ」',
     '九州抗争中、文化街の常連客の減少率は推定6割。'
     '夜の人通りが激減し、店舗の閉店ラッシュが進んだ。'
     '6年に及ぶ「夜の静けさ」は街の経済の根を傷めた、と地元紙連載は記録する。',
     5, '平成抗争', '市民側', 'ku_bunkagai_serial'),

    (1320, 'amagi_periphery', '2010s',
     '甘木の住民 — 「銃声を初めて聞いた」',
     '朝倉市甘木地区の住民取材では「平和な田舎町で銃声を聞くとは思わなかった」 '
     '「ヤクザは別世界だと思っていた」という素朴な驚きの声が記録された。'
     '抗争の地理的広がりが地方都市の認識を変えた事例。',
     4, '平成抗争', '市民側', 'ku_amagi_attack'),

    (1330, 'kurume_keisatsu', '2006-2013',
     '県警 — 6年間の特別警戒',
     '福岡県警の九州抗争対応は、捜査員数百人規模を6年間維持する稀有な事例。'
     '頂上作戦と並走する形で県警組織犯罪対策の能力を高めた、と関連書籍は整理する。',
     4, '平成抗争', '県警側', 'ku_book_dojinkai'),

    (1340, 'kurume_seidokai_hq', '2013-06',
     '九州誠道会 — 解散届提出当日',
     '2013年6月、九州誠道会が解散届を提出した日。'
     '地元紙の写真記録には、本部前で報道陣に囲まれる組関係者の絵が残る。'
     '「組を維持する道筋がない」という事実上の白旗だった、と関連書籍は描く。',
     5, '平成抗争', '道仁会系', 'ku_seidokai_disband'),

    (1350, 'kurume_namikawakai_hq', '2013-07-',
     '浪川会 — 「同じ組を別の名前で続ける」',
     '2013年の浪川会結成は、組織形態を維持しながら名称・看板を変える方式。'
     '事実上の同一組織継承だが、特定抗争指定の対象としては別組織として扱われた。'
     '法制度と実態の乖離を示す事例として議論された。',
     4, '解体後', '道仁会系', 'ku_namikawakai_form'),

    (1360, 'kurume_dojinkai_main_hq', '2014-',
     '道仁会 — 抗争終結後の存続',
     '九州抗争終結後の道仁会は、事務所縮小・組員減少を続けながらも '
     '指定暴力団としての登録は維持。'
     '工藤會本部解体(2019)とは対照的に、組織形態が静かに残る経路を取った。',
     3, '解体後', '道仁会系', 'ku_book_dojinkai'),

    (1370, 'kurume_shrine_temple', '2013-12',
     '抗争終結後 初の冬まつり',
     '2013年の抗争終結後、初の冬の例祭で「街に活気が戻った」 '
     '「子どもを連れて夜歩ける」という住民の声が地元紙に記録された。'
     '街の側が日常を取り戻す節目。',
     4, '解体後', '市民側', 'ku_takara_dais'),

    (1380, 'kurume_bunkagai_central', '2018-',
     '文化街 — 新世代店主の登場',
     '抗争終結から5年、文化街には新世代の店主が登場。'
     '「九州抗争を知らない世代」の店舗が増え、街の世代交代が進んだ。'
     '九州ヤクザ史の節目として地元紙連載は記録する。',
     3, '解体後', '市民側', 'ku_post_2013'),
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

    ev_inserted = 0
    missing = set()
    for (slug, src_key, kind, date, title, summary, victim, weapon, resolution,
         era, faction, severity) in EVENTS:
        site_id = s_ids.get(slug)
        if site_id is None:
            missing.add(slug); continue
        src_id = src_ids.get(src_key)
        cur.execute(
            'DELETE FROM event WHERE site_id=? AND COALESCE(happened_on,"")=? AND title=?',
            (site_id, date or '', title),
        )
        cur.execute(
            'INSERT INTO event(kind, happened_on, site_id, title, summary, '
            ' victim_role, weapon, resolution, source_id, era_tag, faction_tag, severity) '
            ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
            (kind, date, site_id, title, summary, victim, weapon, resolution,
             src_id, era, faction, severity),
        )
        ev_inserted += 1

    lr_inserted = 0
    for (ord_, slug, year, title, body, spice, era, faction, src_key) in LORE:
        site_id = s_ids.get(slug) if slug else None
        if slug and site_id is None:
            missing.add(slug); continue
        src_id = src_ids.get(src_key) if src_key else None
        cur.execute(
            'DELETE FROM lore WHERE COALESCE(site_id, 0)=COALESCE(?, 0) '
            'AND COALESCE(year_label,"")=? AND title=?',
            (site_id, year or '', title),
        )
        cur.execute(
            'INSERT INTO lore(ord, site_id, year_label, title, body, spice, '
            ' era_tag, faction_tag, source_id) VALUES (?,?,?,?,?,?,?,?,?)',
            (ord_, site_id, year, title, body, spice, era, faction, src_id),
        )
        lr_inserted += 1

    con.commit()
    print(f'phase19_kurume: +{ev_inserted} events, +{lr_inserted} lore')
    if missing:
        print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
