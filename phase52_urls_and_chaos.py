"""Phase 52: 主要事件の URL 補完 + 街のカオス情報追加。

ユーザー方針:
  「URL補完。ナレーションは観測事実ベースなら OK。雑多な情報が上げられれば
   そのカオスで街になる」

(1) URL補完: WebSearch 確認済の URL を主要事件 source に紐づけ
(2) 新規 source: Wikipedia + 報道記事 + 公式リリースで実 URL 確定
(3) 雑多な街色: 北九州の名物食・スポーツ・著名出身者・関連サブカルチャー

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


# 新規 source(実 URL 付)
NEW_SOURCES = [
    # 海老蔵事件
    ('s52_nikkei_ebizo', 'news', '日本経済新聞',
     '海老蔵さん事件、26歳男を逮捕 傷害容疑認める(2010-12)',
     'https://www.nikkei.com/article/DGXNASDG10054_Q0A211C1CC1000/', '2010-12'),
    ('s52_wiki_ebizo', 'news', 'Wikipedia',
     '11代目市川海老蔵暴行事件',
     'https://ja.wikipedia.org/wiki/11%E4%BB%A3%E7%9B%AE%E5%B8%82%E5%B7%9D%E6%B5%B7%E8%80%81%E8%94%B5%E6%9A%B4%E8%A1%8C%E4%BA%8B%E4%BB%B6',
     '2010'),
    # 山一抗争
    ('s52_wiki_yamaichi', 'news', 'Wikipedia',
     '山一抗争 — 1984-1989 山口組 vs 一和会',
     'https://ja.wikipedia.org/wiki/%E5%B1%B1%E4%B8%80%E6%8A%97%E4%BA%89',
     '1984-1989'),
    ('s52_wiki_takenaka', 'news', 'Wikipedia',
     '竹中正久 — 四代目山口組組長 1985-01-26 射殺',
     'https://ja.wikipedia.org/wiki/%E7%AB%B9%E4%B8%AD%E6%AD%A3%E4%B9%85',
     '1985-01-26'),
    ('s52_bunshun_yamaichi', 'news', '文春オンライン',
     '《事件317件、25人死亡》暴力団史上最悪の「山一抗争」で生まれた「トップは殺らない」教訓',
     'https://bunshun.jp/articles/-/39832', '2020'),
    # 広島抗争
    ('s52_wiki_hiroshima', 'news', 'Wikipedia',
     '広島抗争 — 1950-1972 第二次広島抗争',
     'https://ja.wikipedia.org/wiki/%E5%BA%83%E5%B3%B6%E6%8A%97%E4%BA%89',
     '1950-1972'),
    ('s52_wiki_jingi', 'news', 'Wikipedia',
     '仁義なき戦い — 美能幸三手記から深作映画へ',
     'https://ja.wikipedia.org/wiki/%E4%BB%81%E7%BE%A9%E3%81%AA%E3%81%8D%E6%88%A6%E3%81%84',
     '1970-1974'),
    # 黒い霧
    ('s52_wiki_kuroi', 'news', 'Wikipedia',
     '黒い霧事件(日本プロ野球)',
     'https://ja.wikipedia.org/wiki/%E9%BB%92%E3%81%84%E9%9C%A7%E4%BA%8B%E4%BB%B6_(%E6%97%A5%E6%9C%AC%E3%83%97%E3%83%AD%E9%87%8E%E7%90%83)',
     '1969-1971'),
    ('s52_seibu_lions_1969', 'official_release', '埼玉西武ライオンズ',
     '1969年 中西、稲尾引退、そして球界に激震が走る',
     'https://www.seibulions.jp/expansion/history/lions_classic/44.html', '1969'),
    # みずほ業務改善命令
    ('s52_fsa_mizuho_2013', 'official_release', '金融庁',
     '株式会社みずほ銀行に対する行政処分(2013-09-27)',
     'https://www.fsa.go.jp/news/25/ginkou/20130927-3.html', '2013-09-27'),
    ('s52_fsa_mizuho_dec', 'official_release', '金融庁',
     'みずほ銀行・みずほFG に対する行政処分(2013-12-26)',
     'https://www.fsa.go.jp/news/25/ginkou/20131226-1.html', '2013-12-26'),
    ('s52_wiki_mizuho', 'news', 'Wikipedia',
     'みずほ銀行暴力団融資事件',
     'https://ja.wikipedia.org/wiki/%E3%81%BF%E3%81%9A%E3%81%BB%E9%8A%80%E8%A1%8C%E6%9A%B4%E5%8A%9B%E5%9B%A3%E8%9E%8D%E8%B3%87%E4%BA%8B%E4%BB%B6',
     '2013'),
    ('s52_nikkei_mizuho', 'news', '日本経済新聞',
     'みずほ銀に業務改善命令 反社会的勢力と取引放置',
     'https://www.nikkei.com/article/DGXNASGC27019_X20C13A9EE8000/', '2013-09'),
    # ロッキード
    ('s52_wiki_lockheed', 'news', 'Wikipedia',
     'ロッキード事件 — 1976-1983 田中角栄逮捕・有罪判決',
     'https://ja.wikipedia.org/wiki/%E3%83%AD%E3%83%83%E3%82%AD%E3%83%BC%E3%83%89%E4%BA%8B%E4%BB%B6',
     '1976-1983'),
    ('s52_nikkei_tanaka_arrest', 'news', '日本経済新聞',
     '1976年7月27日 田中前首相を逮捕',
     'https://www.nikkei.com/article/DGKDZO32815150U1A720C1KB2000/', '1976-07-27'),
    # 阪神大震災 山口組
    ('s52_bunshun_quake', 'news', '文春オンライン',
     '阪神・淡路大震災のときは山口組のテキヤに長蛇の列ができた — 元組長証言',
     'https://bunshun.jp/articles/-/76878', '1995'),
    ('s52_jbpress_quake', 'news', 'JBpress',
     'なぜ阪神淡路大震災では「火事場泥棒」が少なかったのか?',
     'https://jbpress.ismedia.jp/articles/-/93647', '2024'),
    # 関東連合
    ('s52_wiki_kanto_rengo', 'news', 'Wikipedia',
     '関東連合 — 半グレ代表団体・2014年事実上壊滅',
     'https://ja.wikipedia.org/wiki/%E9%96%A2%E6%9D%B1%E9%80%A3%E5%90%88', '2014'),
    ('s52_nikkei_mitate', 'news', '日本経済新聞',
     '六本木クラブ襲撃・見立真一容疑者の似顔絵公開 国際手配',
     'https://www.nikkei.com/article/DGXZQOUE295GR0Z20C24A8000000/', '2024'),
    ('s52_yahoo_mitate', 'news', '弁護士JPニュース / Yahoo!ニュース',
     '見立真一は今どこへ? 「日本に未練はない」2億円手に逃亡か',
     'https://news.yahoo.co.jp/articles/ee8b10ad9e8985046e7bcfd7bb4eac9dc73143ac', '2024'),
]


# (event slug 部分一致, source_id にする source key)
# slug を含むサイトの events の source_id を更新
EVENT_URL_PATCHES = [
    ('roppongi_clubs_hangure',    's52_nikkei_ebizo'),
    ('kobe_yamaichi_ground_zero', 's52_wiki_yamaichi'),
    ('hiroshima_yakuza_war',      's52_wiki_hiroshima'),
    ('hiroshima_jingi_movie',     's52_wiki_jingi'),
    ('proyakyu_kuroikiri',        's52_wiki_kuroi'),
    ('mizuho_bank_hq',            's52_fsa_mizuho_2013'),
    ('lockheed_scandal',          's52_wiki_lockheed'),
    ('kansai_quake_yamaguchi',    's52_bunshun_quake'),
    ('kanto_rengo_hq',            's52_wiki_kanto_rengo'),
    ('roppongi_flower_attack',    's52_nikkei_mitate'),
]


# 雑多な街色: 北九州ベース(街のカオスを上げる)
# (slug, kind, label, lat, lon, unc, first_seen, last_seen, status, notes,
#  era_tag, faction_tag)
NEW_SITES = [
    ('yakiudon_origin',
     '小倉発祥 焼きうどん(だるま堂・1945)',
     6, 33.8866, 130.8806, 500,
     'lore_site', '1945', None, 'active',
     '小倉北区魚町2-2-1のだるま堂が1945年に焼きうどん発祥。'
     '小倉のソウルフードとして全国に広まった。'
     '具材は豚肉・キャベツ・もやし・天かす、'
     '焼きそば麺ではなく茹でた乾麺が伝統。',
     '戦後闇市', '市民側'),

    ('moji_yaki_curry',
     '門司港 焼きカレー',
     6, 33.9447, 130.9628, 500,
     'lore_site', '1950s', None, 'active',
     '門司港地区発祥の焼きカレー。'
     '昭和20年代後半に港町の喫茶店で生まれたとされ、'
     'ご飯にカレーをかけた上にチーズと卵を載せてオーブンで焼く。'
     '門司港レトロ観光と並走で全国に広まった。',
     '戦後闇市', '市民側'),

    ('nukadakimoto',
     '小倉 ぬか炊き',
     6, 33.886, 130.882, 200,
     'lore_site', '1600s', None, 'active',
     '小倉藩の細川忠興時代から続くぬか床料理。'
     '青魚(サバ・イワシ)をぬかで炊く独自の調理法。'
     '北九州の家庭料理として継承されてきた郷土食。',
     '戦後闇市', '市民側'),

    ('giravanz_kitakyushu',
     'ギラヴァンツ北九州(J2)— ミクニワールドスタジアム',
     6, 33.8868, 130.8848, 200,
     'lore_site', '2010', None, 'active',
     'J2 リーグのギラヴァンツ北九州。2010年 J 加入、'
     '2017年 J3 降格 → 2019年 J2 復帰。'
     '本拠地はミクニワールドスタジアム北九州(JR小倉駅から徒歩7分)。'
     '北九州市民のサッカークラブとして地域連携活動も活発。',
     '解体後', '市民側'),

    ('kitakyushu_medi_dome',
     '北九州メディアドーム(競輪場)',
     6, 33.8825, 130.8917, 300,
     'lore_site', '1998', None, 'active',
     '小倉北区三萩野3丁目1-1のメディアドーム(1998年開業)。'
     '日本初のドーム型競輪場。北九州競輪の本拠地。'
     '北九州中央公園の一角で、地域住民の通り道。',
     '解体後', '市民側'),

    ('boatrace_wakamatsu',
     'ボートレース若松',
     6, 33.9166, 130.8225, 500,
     'lore_site', '1952', None, 'active',
     '若松区赤岩町のボートレース若松。1952年開場。'
     '日本初の競艇場の一つで、若松区民の生活に深く根付いた競技場。'
     '夜開催「ナイトレース」発祥地としても知られる。',
     '高度成長', '市民側'),

    ('kitakyushu_zoo',
     '到津の森公園(動物園)',
     6, 33.8773, 130.8627, 300,
     'lore_site', '1932', None, 'active',
     '小倉北区上到津4-1-8の到津の森公園。1932年開園の市営動物園。'
     '北九州市民が子どもの頃に遠足で行く定番。'
     '解体危機後に2002年再開園、地域住民の支援で復活した経緯を持つ。',
     '戦後闇市', '市民側'),

    ('kokura_jigon_drum',
     '小倉祇園太鼓 — 7月3週末',
     6, 33.8856, 130.8765, 400,
     'lore_site', '1617', None, 'active',
     '小倉北区中心市街地で毎年7月の第3金土日に開催される祭り。'
     '小倉藩細川忠興時代の1617年起源とされる伝統祭事。'
     '映画「無法松の一生」のモデルとなった祭り。'
     '太鼓の両面打ちが特徴の独特の祇園祭。',
     '戦後闇市', '市民側'),

    ('tobata_giant_yamagasa',
     '戸畑祇園大山笠 — 7月4週末',
     6, 33.8919, 130.8333, 400,
     'lore_site', '1802', None, 'active',
     '戸畑区天籟寺の戸畑祇園大山笠。1802年起源、ユネスコ無形文化遺産。'
     '昼の幟大山笠が夕方提灯山笠に変身する独特の祭り。'
     '北九州5市合併前から続く戸畑独自の伝統。',
     '戦後闇市', '市民側'),

    ('yawata_matsuri',
     '八幡まつり — 7月最終週末',
     6, 33.8638, 130.7195, 400,
     'lore_site', '1900s', None, 'active',
     '八幡西区黒崎の八幡まつり。'
     '北九州5市合併前の旧八幡市時代から続く伝統祭事。'
     '製鐵所労働者の街を背景とした昭和的祭事の継承。',
     '戦後闇市', '市民側'),

    ('takakura_ken_birthplace',
     '高倉健 — 中間市出身',
     6, 33.8164, 130.7100, 1000,
     'lore_site', '1931-02-16', '2014-11-10', 'active',
     '昭和の映画俳優 高倉健(1931-2014)は福岡県中間市出身。'
     '北九州市の隣接市から東映任侠映画の最重要俳優へ。'
     '「網走番外地」「昭和残侠伝」「幸福の黄色いハンカチ」 — '
     '戦後日本映画史の重要人物。',
     '戦後闇市', '著作者'),

    ('matsumoto_leiji_birthplace',
     '松本零士 — 北九州市小倉北区出身',
     6, 33.8852, 130.88, 1000,
     'lore_site', '1938-01-25', '2023-02-13', 'active',
     '漫画家 松本零士(1938-2023)は北九州市小倉北区出身。'
     '「銀河鉄道999」「宇宙戦艦ヤマト」「キャプテンハーロック」 — '
     '日本 SF 漫画史の最重要人物。'
     '小倉北区中心部の風景は彼の作品の原風景。',
     '戦後闇市', '著作者'),

    ('hojo_tsukasa_birthplace',
     '北条司 — 北九州市小倉北区出身',
     6, 33.8852, 130.88, 1000,
     'lore_site', '1959-03-05', None, 'active',
     '漫画家 北条司(1959-)は北九州市小倉北区出身。'
     '「キャッツ・アイ」「シティハンター」「エンジェル・ハート」 — '
     '1980-90 年代の少年ジャンプ黄金期の重要作品。',
     '高度成長', '著作者'),

    ('robert_akiyama_birthplace',
     'ロバート秋山 — 北九州市門司区出身',
     6, 33.9447, 130.9628, 1000,
     'lore_site', '1981-08-15', None, 'active',
     'お笑い芸人 ロバート秋山竜次(1981-)は北九州市門司区出身。'
     '「クリエイターズ・ファイル」など SNS 発の人気企画。'
     '北九州弁を駆使した独特の話術。',
     '解体後', '著作者'),

    ('suzuki_kosuke_birthplace',
     '鈴木浩介 — 北九州市八幡西区出身',
     6, 33.8638, 130.7195, 1000,
     'lore_site', '1974-03-05', None, 'active',
     '俳優 鈴木浩介(1974-)は北九州市八幡西区出身。'
     '舞台・映画・テレビドラマで幅広く活動。'
     '北九州弁を自然に使う芸風で地元では特に親しまれる。',
     '解体後', '著作者'),

    ('uomachi_chinese_chinatown',
     '小倉北区魚町 中華街',
     6, 33.8857, 130.8806, 200,
     'lore_site', '1950s', None, 'active',
     '小倉北区魚町2丁目周辺の小さな中華街。'
     '戦後の華僑コミュニティが形成した、九州最大級の中華料理店集積エリア。'
     '横浜・神戸・長崎ほどの規模はないが、小倉の食文化の重要な一角。',
     '戦後闇市', '市民側'),

    ('kitakyushu_mahjong_culture',
     '北九州 麻雀文化',
     6, 33.8857, 130.882, 1000,
     'lore_site', '1950s', None, 'active',
     '北九州市は戦後の重工業労働者文化を背景に、麻雀店が多い街。'
     '小倉北区・八幡東区・戸畑区に老舗の雀荘が散在。'
     '昭和の労働者の余暇文化の継承として現在も営業。',
     '戦後闇市', '市民側'),

    ('compound_time_machine_sister',
     'Compound Time Machine — 姉妹プロジェクト',
     6, 16.0, 100.0, 1000000,
     'lore_site', '2024', None, 'active',
     'メコン地域のオンライン詐欺コンパウンドを衛星画像で詳述する '
     'OSINT 姉妹プロジェクト。https://compoundtimemachine.com'
     '本マップ(Kokura Underworld Map)はここから派生。'
     '日本トクリュウとの接続事例が現代の研究テーマ。',
     '解体後', 'トクリュウ'),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # (1) 新規 source 投入
    src_inserted = 0
    src_ids = {}
    for key, kind, outlet, title, url, pub in NEW_SOURCES:
        cur.execute(
            "DELETE FROM source WHERE outlet=? AND title=? AND COALESCE(published_on,'')=?",
            (outlet, title, pub or ''))
        cur.execute(
            'INSERT INTO source(kind, outlet, title, url, published_on) '
            'VALUES (?,?,?,?,?)',
            (kind, outlet, title, url, pub))
        src_ids[key] = cur.lastrowid
        src_inserted += 1
    print(f'New sources: {src_inserted}')

    # (2) 既存 event の source_id を新 URL 付 source に張り替え
    sites = {row[1]: row[0] for row in cur.execute('SELECT id, slug FROM site')}
    patches = 0
    for slug, src_key in EVENT_URL_PATCHES:
        sid = sites.get(slug)
        if sid is None: continue
        src_id = src_ids.get(src_key)
        if src_id is None: continue
        n = cur.execute(
            'UPDATE event SET source_id = ? WHERE site_id = ? AND source_id IS NULL',
            (src_id, sid)).rowcount
        if n:
            print(f'  {slug}: {n} events linked to {src_key}')
            patches += n
        # またこの slug の既存 events で source_id が generic homepage URL なら張り替え
        n2 = cur.execute(
            'UPDATE event SET source_id = ? '
            'WHERE site_id = ? AND source_id IN ('
            '  SELECT id FROM source WHERE url IS NULL OR url GLOB "*://*/" )',
            (src_id, sid)).rowcount
        if n2:
            print(f'  {slug}: +{n2} events upgraded URL')
            patches += n2

    # (3) 新規サイト(雑多な街色)を init_db.py の SITES とは別に挿入
    cur.execute("SELECT id FROM place WHERE name_canonical='北九州市小倉北区'")
    pl_kokurakita = cur.fetchone()[0]
    cur.execute("SELECT id FROM place WHERE name_canonical='北九州市門司区'")
    pl_moji = cur.fetchone()[0]
    cur.execute("SELECT id FROM place WHERE name_canonical='北九州市八幡西区'")
    pl_yahatanishi = cur.fetchone()[0]
    cur.execute("SELECT id FROM place WHERE name_canonical='北九州市戸畑区'")
    pl_tobata = cur.fetchone()[0]
    cur.execute("SELECT id FROM place WHERE name_canonical='北九州市若松区'")
    pl_wakamatsu = cur.fetchone()[0]
    cur.execute("SELECT id FROM place WHERE name_canonical='北九州市八幡東区'")
    pl_yahatahigashi = cur.fetchone()[0]

    pl_by_slug = {
        'yakiudon_origin': pl_kokurakita,
        'moji_yaki_curry': pl_moji,
        'nukadakimoto': pl_kokurakita,
        'giravanz_kitakyushu': pl_kokurakita,
        'kitakyushu_medi_dome': pl_kokurakita,
        'boatrace_wakamatsu': pl_wakamatsu,
        'kitakyushu_zoo': pl_kokurakita,
        'kokura_jigon_drum': pl_kokurakita,
        'tobata_giant_yamagasa': pl_tobata,
        'yawata_matsuri': pl_yahatanishi,
        'takakura_ken_birthplace': pl_kokurakita,  # 中間市は別 place が必要だが暫定
        'matsumoto_leiji_birthplace': pl_kokurakita,
        'hojo_tsukasa_birthplace': pl_kokurakita,
        'robert_akiyama_birthplace': pl_moji,
        'suzuki_kosuke_birthplace': pl_yahatanishi,
        'uomachi_chinese_chinatown': pl_kokurakita,
        'kitakyushu_mahjong_culture': pl_kokurakita,
        'compound_time_machine_sister': None,
    }
    new_sites_added = 0
    for tpl in NEW_SITES:
        slug = tpl[0]
        # Insert or update
        pid = pl_by_slug.get(slug)
        existing = cur.execute('SELECT id FROM site WHERE slug = ?', (slug,)).fetchone()
        if existing:
            continue  # skip if exists
        cur.execute(
            'INSERT INTO site(slug, label, place_id, rep_lat, rep_lon, uncertainty_m, kind, '
            ' first_seen, last_seen, status, notes, era_tag, faction_tag) '
            'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (tpl[0], tpl[1], pid, tpl[3], tpl[4], tpl[5], tpl[6], tpl[7],
             tpl[8], tpl[9], tpl[10], tpl[11], tpl[12]))
        new_sites_added += 1

    con.commit()
    total_sources = cur.execute('SELECT COUNT(*) FROM source').fetchone()[0]
    total_sites = cur.execute('SELECT COUNT(*) FROM site').fetchone()[0]
    story_urls = cur.execute(
        "SELECT COUNT(*) FROM source WHERE url IS NOT NULL AND url <> '' "
        "AND url NOT GLOB '*://*/' AND url LIKE '%/%/%'"
    ).fetchone()[0]
    print(f'\nTotals:')
    print(f'  sources: {total_sources}({story_urls} with story-specific URL)')
    print(f'  sites: {total_sites}')
    print(f'  new sites added: {new_sites_added}')
    print(f'  event URL patches: {patches}')
    con.close()


if __name__ == '__main__':
    main()
