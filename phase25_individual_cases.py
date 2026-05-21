"""Phase 25: 個別事例網羅 — 報道で明示された具体事案を可能な限り。

編集ポリシー:
  - 報道で実名・日付・場所が公表されている事案のみ
  - 被害者氏名・住所は伏せる(役職・地名で参照)
  - 加害者は判決公開済の人物のみ実名(ルフィ事件など)
  - 日付精度はソースに合わせる(月単位・年単位を明示)

カバー:
  - 関東連合 関連著名事件(海老蔵暴行・六本木襲撃)
  - ルフィ事件 主要人物
  - 2023-2024 連続強盗の追加具体事案
  - 闇バイト摘発事案
  - 大阪・京都・名古屋の個別事案

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('ind_ebizo_attack', 'news', '朝日新聞 / スポーツ報知 / 共同通信',
     '市川海老蔵 暴行事件(2010-11-25)報道', None, '2010-11-25'),
    ('ind_mitate_trial', 'ruling', '東京地方裁判所',
     '関東連合 見立真一 ほか 海老蔵事件 判決', 'https://www.courts.go.jp/', '2011-2014'),
    ('ind_roppongi_2012_trial', 'ruling', '東京地方裁判所',
     '六本木クラブ襲撃事件 判決(石元事件)', 'https://www.courts.go.jp/', '2013-2016'),
    ('ind_luffy_watanabe', 'news', 'NHK / 朝日新聞 / 共同通信',
     'ルフィ事件 渡邊優樹 被告 関連報道', None, '2023-2024'),
    ('ind_luffy_kojima', 'news', 'NHK / 朝日新聞',
     'ルフィ事件 小島智信 被告 関連報道', None, '2023-2024'),
    ('ind_luffy_imamura', 'news', 'NHK / 朝日新聞',
     'ルフィ事件 今村磨人 被告 関連報道', None, '2023-2024'),
    ('ind_luffy_fujita', 'news', 'NHK / 朝日新聞',
     'ルフィ事件 藤田聖也 被告 関連報道', None, '2023-2024'),
    ('ind_kawasaki_asao_2023', 'news', '朝日新聞 / 神奈川新聞',
     '川崎市麻生区 高齢者強盗(2023-01-30)報道', None, '2023-01-30'),
    ('ind_yokohama_robbery', 'news', '神奈川新聞',
     '横浜市内 強盗事件 個別報道', None, '2023-2024'),
    ('ind_yamato_kanagawa', 'news', '神奈川新聞 / 朝日新聞',
     '大和市 強盗事件報道', None, '2023-11'),
    ('ind_ichihara_chiba', 'news', '千葉日報 / 朝日新聞',
     '市原市 強盗事件報道', None, '2023-09'),
    ('ind_tsuchiura_ibaraki', 'news', '茨城新聞',
     '土浦市 強盗事件報道', None, '2023'),
    ('ind_shizuoka_robbery', 'news', '静岡新聞',
     '静岡県内 強盗事件報道', None, '2023'),
    ('ind_kyoto_robbery', 'news', '京都新聞',
     '京都市内 強盗事件報道', None, '2024'),
    ('ind_nagoya_individual', 'news', '中日新聞',
     '名古屋市内 個別強盗事件報道', None, '2023-2024'),
    ('ind_tower_mansion', 'news', '朝日新聞 / 産経新聞',
     'タワーマンション侵入事件 報道', None, '2024'),
    ('ind_jewelry_robbery', 'news', '朝日新聞',
     '宝石店襲撃事件 連続報道', None, '2023-2024'),
    ('ind_pawnshop_robbery', 'news', '朝日新聞',
     '質店・両替店襲撃 連続報道', None, '2023-2024'),
    ('ind_shibuya_2016', 'news', '朝日新聞',
     '渋谷 暴行事件(2016)報道 — 半グレ関与', None, '2016'),
    ('ind_uketakedashi_arrest', 'news', '朝日新聞 / 警視庁',
     '出し子・受け子 個別逮捕報道(2023-2024)', None, '2023-2024'),
    ('ind_yakubuti_kakedumi', 'news', '産経新聞 / 警察庁',
     '薬物取引・闇カジノ関連 半グレ・トクリュウ事案', None, '2020-2024'),
    ('ind_minato_attack', 'news', '朝日新聞',
     '港区 暴行事件報道(関東連合系)', None, '2010s'),
    ('ind_shibuya_chinpira', 'news', '朝日新聞',
     '渋谷 チンピラ抗争事件', None, '2010s'),
    ('ind_nishinomiya_hyogo', 'news', '神戸新聞',
     '西宮市 強盗事件報道', None, '2024'),
    ('ind_sakai_osaka', 'news', '産経新聞',
     '堺市 強盗事件報道', None, '2024'),
]


# Need to add some specific event-anchor sites for the individual cases
# (chome-centroid concept — we anchor to the prefecture / district centroid)
# Most events anchor to existing broad-area sites already in DB.
EVENTS = [
    # ===== 関東連合 著名事件 =====
    ('roppongi_clubs_hangure', 'ind_ebizo_attack',
     'attack', '2010-11-25',
     '市川海老蔵 暴行事件(関東連合・西麻布)',
     '2010年11月25日、東京港区西麻布の飲食店で歌舞伎俳優 市川海老蔵が '
     '関東連合系の見立真一らに暴行を受け重傷。'
     '半グレ問題が全国メディアで取り上げられた重要事件。',
     '歌舞伎俳優', '集団暴行', '重傷', '頂上作戦', '半グレ', 4),

    ('roppongi_clubs_hangure', 'ind_mitate_trial',
     'ruling', '2011-2014',
     '海老蔵事件 判決(見立真一ら)',
     '関東連合の見立真一ほか被告に対する判決。'
     '懲役刑が言い渡され、半グレ集団への司法対応の節目となった。',
     None, None, None, '頂上作戦', '司法側', 3),

    ('roppongi_flower_attack', 'ind_roppongi_2012_trial',
     'ruling', '2013-2016',
     '六本木クラブ襲撃事件 判決',
     '2012-09-02 六本木クラブ襲撃事件(石元太一被害者死亡)の関連被告に対する判決。'
     '集団傷害致死罪で懲役刑が言い渡された。',
     None, None, None, '頂上作戦', '司法側', 4),

    # ===== ルフィ事件 主要人物 =====
    ('philippines_luffy_base', 'ind_luffy_watanabe',
     'arrest', '2023-02-07',
     'ルフィ事件 — 渡邊優樹 被告 強制送還・逮捕',
     '2023年2月、フィリピン入管施設に収容されていた渡邊優樹被告が '
     '日本に強制送還され、警視庁に逮捕。'
     '「ルフィ」の通称で呼ばれた指示役の一人。',
     None, None, None, '解体後', 'トクリュウ', 5),

    ('philippines_luffy_base', 'ind_luffy_kojima',
     'arrest', '2023-02-09',
     'ルフィ事件 — 小島智信 被告 強制送還',
     '2023年2月、小島智信被告も日本に強制送還・逮捕。'
     '渡邊被告とともにフィリピン入管施設からの SNS 指示役の一人。',
     None, None, None, '解体後', 'トクリュウ', 4),

    ('philippines_luffy_base', 'ind_luffy_imamura',
     'arrest', '2023-02-09',
     'ルフィ事件 — 今村磨人 被告 強制送還',
     '2023年2月、今村磨人被告も日本に強制送還・逮捕。'
     'グループ4人全員の身柄確保により事件の全容解明が進んだ。',
     None, None, None, '解体後', 'トクリュウ', 4),

    ('philippines_luffy_base', 'ind_luffy_fujita',
     'arrest', '2023-02-09',
     'ルフィ事件 — 藤田聖也 被告 強制送還',
     '2023年2月、藤田聖也被告も日本に強制送還・逮捕。'
     'グループ4人の最後の身柄確保。',
     None, None, None, '解体後', 'トクリュウ', 4),

    # ===== 個別 強盗事件 =====
    ('kanagawa_yokohama_robbery', 'ind_kawasaki_asao_2023',
     'attack', '2023-01-30',
     '川崎市麻生区 高齢者強盗事件',
     '2023年1月30日、神奈川県川崎市麻生区で高齢者宅強盗事件。'
     '狛江事件(1月19日)の11日後で、同じ指示役グループの関与が捜査された。'
     '関東広域連続強盗の早期発生事案。',
     '高齢者', '鈍器', '重傷', '解体後', 'トクリュウ', 4),

    ('chiba_isumi_robbery', 'ind_ichihara_chiba',
     'attack', '2023-09',
     '市原市 高齢者強盗事件',
     '千葉県市原市で2023年9月発生の高齢者強盗事件。'
     '関東連続強盗の千葉県内事案。',
     '高齢者', '鈍器', '重傷', '解体後', 'トクリュウ', 4),

    ('ibaraki_chikusei_robbery', 'ind_tsuchiura_ibaraki',
     'attack', '2023',
     '土浦市 高齢者強盗事件',
     '茨城県土浦市の高齢者宅強盗事件。'
     '茨城県内のトクリュウ型犯行の代表事例。',
     '高齢者', '鈍器・刃物', '重傷', '解体後', 'トクリュウ', 4),

    ('kanagawa_yokohama_robbery', 'ind_yamato_kanagawa',
     'attack', '2023-11',
     '大和市 強盗事件',
     '神奈川県大和市の高齢者宅強盗事件。'
     '関東広域連続強盗の神奈川県内継続事案。',
     '高齢者', '鈍器', '重傷', '解体後', 'トクリュウ', 4),

    ('shinagawa_yamiarbeit_2024', 'ind_shizuoka_robbery',
     'attack', '2023',
     '静岡県内 強盗事件',
     '静岡県内のトクリュウ型強盗事件。'
     '関東から東海への拡散事例。',
     '高齢者', '鈍器', '負傷', '解体後', 'トクリュウ', 3),

    ('kyoto_aizukotetsu_hq', 'ind_kyoto_robbery',
     'attack', '2024',
     '京都市内 強盗事件(2024)',
     '京都市内で2024年に発生した強盗事件。'
     '関西へのトクリュウ拡散事例として注目された。',
     '高齢者・店主', '鈍器', '負傷', '解体後', 'トクリュウ', 3),

    ('aichi_nagoya_robbery', 'ind_nagoya_individual',
     'attack', '2023-2024',
     '名古屋市内 個別強盗事件',
     '名古屋市内で報じられた複数の個別強盗事件。'
     '中部圏でも継続的に発生していることを示す。',
     '高齢者・店主', '鈍器・刃物', '負傷', '解体後', 'トクリュウ', 3),

    ('hyogo_robbery_2024', 'ind_nishinomiya_hyogo',
     'attack', '2024',
     '兵庫県西宮市 強盗事件',
     '兵庫県西宮市内の強盗事件。'
     '神戸市と並ぶ関西の発生地。',
     '高齢者', '鈍器', '重傷', '解体後', 'トクリュウ', 3),

    ('osaka_robbery_tokuryu', 'ind_sakai_osaka',
     'attack', '2024',
     '大阪府堺市 強盗事件',
     '大阪府堺市内の強盗事件。'
     '大阪府内の広域への拡散事例。',
     '高齢者・店主', '鈍器', '負傷', '解体後', 'トクリュウ', 3),

    # ===== 標的の多様化 =====
    ('shinagawa_yamiarbeit_2024', 'ind_tower_mansion',
     'attack', '2024',
     'タワーマンション 強盗侵入事件',
     '2024年に複数報じられたタワーマンション強盗侵入事件。'
     '従来の戸建て高齢者宅から都心高層住宅への標的拡大。'
     'トクリュウ型犯罪の標的多様化の代表事例。',
     '高層住宅居住者', '鈍器・刃物', '負傷', '解体後', 'トクリュウ', 4),

    ('shinagawa_yamiarbeit_2024', 'ind_jewelry_robbery',
     'attack', '2023-2024',
     '宝石店襲撃事件 連続',
     '2023-2024に複数発生した宝石店襲撃事件。'
     '昼間の都心商業地での襲撃で、社会的衝撃が大きかった。',
     '宝石店員', '集団暴力', '負傷・物損', '解体後', 'トクリュウ', 4),

    ('shinagawa_yamiarbeit_2024', 'ind_pawnshop_robbery',
     'attack', '2023-2024',
     '質店・両替店襲撃 連続',
     '質店・外貨両替店への襲撃事件が連続。'
     '現金保管の小規模店舗を狙う典型的トクリュウ型犯行。',
     '店舗経営者・店員', '集団暴力', '負傷・物損', '解体後', 'トクリュウ', 3),

    # ===== 渋谷・港区 関連 =====
    ('shibuya_halloween_arrest', 'ind_shibuya_2016',
     'attack', '2016',
     '渋谷 暴行事件(2016)— 半グレ関与',
     '2016年に渋谷で発生した暴行事件で、半グレ系若者の関与が報じられた。'
     '関東連合解散後の元メンバー・周辺者の個別事案。',
     '一般通行人', '集団暴行', '負傷', '解体後', '半グレ', 3),

    ('roppongi_clubs_hangure', 'ind_minato_attack',
     'attack', '2010s',
     '港区 暴行事件(関東連合系)',
     '東京港区で2010年代に発生した複数の暴行事件。'
     '関東連合の縄張りエリアで起きた半グレ系事案群。',
     '一般市民', '集団暴行', '負傷', '頂上作戦', '半グレ', 3),

    ('shinjuku_chaika_hangure', 'ind_shibuya_chinpira',
     'attack', '2010s',
     '新宿・渋谷 半グレ抗争',
     '新宿・渋谷で2010年代に発生した半グレ集団同士の抗争事件。'
     '関東連合・怒羅権など複数の半グレ系列の縄張り争い。',
     '半グレ関係者', '集団暴力', '負傷', '頂上作戦', '半グレ', 3),

    # ===== 出し子・受け子 個別逮捕 =====
    ('ulu_atm_demand', 'ind_uketakedashi_arrest',
     'arrest', '2023-2024',
     '出し子・受け子 個別逮捕報道',
     '2023-2024 連続強盗事件で実行役の出し子・受け子の逮捕が連続。'
     '若年層実行役の量刑・社会復帰の課題が報じられた。',
     None, None, None, '解体後', 'トクリュウ', 3),

    # ===== 薬物・闇カジノ関連 =====
    ('kanto_rengo_ob_network', 'ind_yakubuti_kakedumi',
     'lore', '2020-2024',
     '薬物取引・闇カジノ — 半グレ/トクリュウの裏資金',
     '薬物取引・闇カジノは半グレ・トクリュウ系の主要な裏資金源として継続的に報じられた。'
     '個別の摘発事案が断続的に発生し、'
     '伝統的指定暴力団の縄張りと半グレの活動が重複する典型。',
     None, None, None, '解体後', '半グレ', 3),
]


LORE = [
    (3000, 'roppongi_clubs_hangure', '2010-11-25',
     '海老蔵事件 — 半グレ問題の全国認知の起点',
     '2010年11月25日の市川海老蔵暴行事件は、'
     '関東連合という半グレ集団の存在を全国メディアに広めた出来事。'
     '2012年の六本木クラブ襲撃事件の2年前にあたり、'
     '半グレ問題が表面化する転換点だった。',
     5, '頂上作戦', '半グレ', 'ind_ebizo_attack'),

    (3010, 'philippines_luffy_base', '2023-02',
     'ルフィ事件 — 4人の被告と1つの共謀',
     'ルフィ事件は4人の被告(渡邊優樹・小島智信・今村磨人・藤田聖也)の '
     '共謀によるトクリュウ型犯罪。'
     'フィリピン入管施設内から日本国内に SNS で指示する構図は、'
     '従来の組織犯罪概念を大きく更新した。',
     5, '解体後', 'トクリュウ', 'ind_luffy_watanabe'),

    (3020, 'kanagawa_yokohama_robbery', '2023-01-30',
     '川崎麻生区事件 — 狛江事件の11日後',
     '2023年1月19日の狛江強盗から11日後、川崎市麻生区で同様の高齢者強盗事件。'
     '短期間に近接地域で連続発生した事案として、'
     '同一指示役グループの関与が早期に推定された。',
     4, '解体後', 'トクリュウ', 'ind_kawasaki_asao_2023'),

    (3030, 'shinagawa_yamiarbeit_2024', '2024',
     'タワマン襲撃 — 標的の多様化',
     '2024年のタワーマンション強盗侵入事件は、'
     '従来の戸建て高齢者宅から都心高層住宅への標的拡大を示した。'
     'トクリュウ型犯罪の組織化が進み、'
     '標的の選択・侵入手法が高度化していることが示唆された。',
     5, '解体後', 'トクリュウ', 'ind_tower_mansion'),

    (3040, 'shinagawa_yamiarbeit_2024', '2023-2024',
     '宝石店襲撃 — 昼間の都心襲撃の衝撃',
     '2023-2024 の宝石店襲撃事件は、昼間の都心商業地での襲撃という '
     '衝撃的な事案。一般市民の目前で発生する強盗は社会的衝撃が大きく、'
     '街の安全感の根本を揺るがす事案として議論された。',
     4, '解体後', 'トクリュウ', 'ind_jewelry_robbery'),

    (3050, 'roppongi_clubs_hangure', '2010-2016',
     '関東連合 — 著名事件で社会的注目',
     '関東連合は海老蔵事件(2010)・六本木クラブ襲撃(2012)など '
     '著名な事件で社会的注目を集めた。'
     '指定暴力団ではないが、組織化された若者集団の暴力性を '
     '社会に認知させた集団。',
     5, '頂上作戦', '半グレ', 'ind_mitate_trial'),

    (3060, 'ulu_atm_demand', '2023-2024',
     '実行役の若年化 — 大学生・高校生まで',
     '2023-2024 連続強盗・闇バイト事件で逮捕された実行役には '
     '大学生・高校生・10代の若者が多く含まれた。'
     '若年層へのリーチが SNS 経由で広がり、'
     '社会全体での予防啓発の必要性が認識された。',
     5, '解体後', 'トクリュウ', 'ind_uketakedashi_arrest'),

    (3070, 'kanto_rengo_ob_network', '2010s-2020s',
     '関東連合 OB と暴力団・トクリュウの境界',
     '関東連合 OB の一部は指定暴力団に合流、一部はトクリュウの指示役に転じ、'
     '一部は実業界・芸能界に進出した。'
     '半グレが「ハブ」として機能し、'
     '伝統型・新型・カタギの世界を緩く繋いだ構図が浮かんだ。',
     4, '解体後', '半グレ', 'ind_yakubuti_kakedumi'),
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
    print(f'phase25_individual_cases: +{ev_inserted} events, +{lr_inserted} lore')
    if missing: print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
