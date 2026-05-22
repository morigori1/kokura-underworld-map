"""Phase 46: 各拠点に地元メディア・行政情報を関連付け。

新規 table local_media を作成し、サイトを都道府県/市町村に分類して
地方紙・テレビ・県/市役所・県警・暴追センターを表示できるようにする。

スキーマ:
  local_media(id, site_id, kind, name, url, note, ord)
    kind: newspaper / tv / radio / magazine /
          pref_gov / city_gov / pref_police / bouhai_center /
          court / library / museum / npo / other

判定ロジック:
  座標(lat)で大まかな region/prefecture を推定、slug 名で細部を確定。

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


# 都道府県 → 標準的な地元メディア / 行政
# (kind, name, url, note)
LOCAL_MEDIA_BY_PREF = {
    '北海道': [
        ('newspaper', '北海道新聞', 'https://www.hokkaido-np.co.jp/', '北海道全道紙'),
        ('tv', 'HBC 北海道放送', 'https://www.hbc.co.jp/', None),
        ('tv', 'STV 札幌テレビ', 'https://www.stv.jp/', None),
        ('pref_gov', '北海道庁', 'https://www.pref.hokkaido.lg.jp/', None),
        ('pref_police', '北海道警察', 'https://www.police.pref.hokkaido.lg.jp/', None),
        ('bouhai_center', '北海道暴力追放センター', 'https://www.h-bouhai.jp/', None),
    ],
    '宮城県': [
        ('newspaper', '河北新報', 'https://www.kahoku.news/', '東北 main 紙'),
        ('tv', '東北放送', 'https://www.tbc-sendai.co.jp/', None),
        ('pref_gov', '宮城県庁', 'https://www.pref.miyagi.jp/', None),
        ('pref_police', '宮城県警察', 'https://www.police.pref.miyagi.jp/', None),
    ],
    '福島県': [
        ('newspaper', '福島民報', 'https://www.minpo.jp/', None),
        ('newspaper', '福島民友', 'https://www.minyu-net.com/', None),
        ('tv', '福島テレビ', 'https://www.fukushima-tv.co.jp/', None),
        ('pref_gov', '福島県庁', 'https://www.pref.fukushima.lg.jp/', None),
        ('pref_police', '福島県警察', 'https://www.police.pref.fukushima.jp/', None),
    ],
    '茨城県': [
        ('newspaper', '茨城新聞', 'https://ibarakinews.jp/', None),
        ('tv', 'IBS 茨城放送', 'https://www.ibs-radio.com/', None),
        ('pref_gov', '茨城県庁', 'https://www.pref.ibaraki.jp/', None),
        ('pref_police', '茨城県警察', 'https://www.pref.ibaraki.jp/keisatsu/', None),
    ],
    '栃木県': [
        ('newspaper', '下野新聞', 'https://www.shimotsuke.co.jp/', None),
        ('pref_gov', '栃木県庁', 'https://www.pref.tochigi.lg.jp/', None),
        ('pref_police', '栃木県警察', 'https://www.pref.tochigi.lg.jp/keisatu/', None),
    ],
    '群馬県': [
        ('newspaper', '上毛新聞', 'https://www.jomo-news.co.jp/', None),
        ('pref_gov', '群馬県庁', 'https://www.pref.gunma.jp/', None),
        ('pref_police', '群馬県警察', 'https://www.police.pref.gunma.jp/', None),
    ],
    '埼玉県': [
        ('newspaper', '埼玉新聞', 'https://www.saitama-np.co.jp/', None),
        ('tv', 'テレ玉(テレビ埼玉)', 'https://www.teletama.jp/', None),
        ('pref_gov', '埼玉県庁', 'https://www.pref.saitama.lg.jp/', None),
        ('pref_police', '埼玉県警察', 'https://www.police.pref.saitama.lg.jp/', None),
    ],
    '千葉県': [
        ('newspaper', '千葉日報', 'https://www.chibanippo.co.jp/', None),
        ('tv', 'チバテレ', 'https://www.chiba-tv.com/', None),
        ('pref_gov', '千葉県庁', 'https://www.pref.chiba.lg.jp/', None),
        ('pref_police', '千葉県警察', 'https://www.police.pref.chiba.jp/', None),
    ],
    '東京都': [
        ('newspaper', '朝日新聞 東京本社', 'https://www.asahi.com/', None),
        ('newspaper', '毎日新聞 東京本社', 'https://mainichi.jp/', None),
        ('newspaper', '読売新聞 東京本社', 'https://www.yomiuri.co.jp/', None),
        ('newspaper', '日本経済新聞', 'https://www.nikkei.com/', None),
        ('newspaper', '東京新聞', 'https://www.tokyo-np.co.jp/', None),
        ('tv', 'NHK 東京', 'https://www.nhk.or.jp/tokyo/', None),
        ('tv', 'TOKYO MX', 'https://www.mxtv.co.jp/', None),
        ('pref_gov', '東京都庁', 'https://www.metro.tokyo.lg.jp/', None),
        ('pref_police', '警視庁', 'https://www.keishicho.metro.tokyo.lg.jp/', None),
        ('bouhai_center', '東京都暴力団追放運動推進センター',
         'https://www.boutsui-tokyo.com/', None),
    ],
    '神奈川県': [
        ('newspaper', '神奈川新聞', 'https://www.kanaloco.jp/', None),
        ('tv', 'tvk テレビ神奈川', 'https://www.tvk-yokohama.com/', None),
        ('pref_gov', '神奈川県庁', 'https://www.pref.kanagawa.jp/', None),
        ('pref_police', '神奈川県警察', 'https://www.police.pref.kanagawa.jp/', None),
    ],
    '新潟県': [
        ('newspaper', '新潟日報', 'https://www.niigata-nippo.co.jp/', None),
        ('tv', 'NHK 新潟', 'https://www.nhk.or.jp/niigata/', None),
        ('pref_gov', '新潟県庁', 'https://www.pref.niigata.lg.jp/', None),
        ('pref_police', '新潟県警察', 'https://www.police.pref.niigata.jp/', None),
    ],
    '富山県': [
        ('newspaper', '北日本新聞', 'https://webun.jp/', None),
        ('pref_gov', '富山県庁', 'https://www.pref.toyama.jp/', None),
        ('pref_police', '富山県警察', 'https://www.pref.toyama.jp/sections/1100/', None),
    ],
    '石川県': [
        ('newspaper', '北國新聞', 'https://www.hokkoku.co.jp/', None),
        ('pref_gov', '石川県庁', 'https://www.pref.ishikawa.lg.jp/', None),
        ('pref_police', '石川県警察', 'https://www.pref.ishikawa.lg.jp/police/', None),
    ],
    '静岡県': [
        ('newspaper', '静岡新聞', 'https://www.at-s.com/', None),
        ('tv', 'SBS 静岡放送', 'https://www.at-s.com/sbstv/', None),
        ('pref_gov', '静岡県庁', 'https://www.pref.shizuoka.jp/', None),
        ('pref_police', '静岡県警察', 'https://www.pref.shizuoka.jp/police/', None),
    ],
    '愛知県': [
        ('newspaper', '中日新聞', 'https://www.chunichi.co.jp/', '中部地方 main 紙'),
        ('tv', 'CBC テレビ', 'https://hicbc.com/', None),
        ('tv', '東海テレビ', 'https://tokai-tv.com/', None),
        ('pref_gov', '愛知県庁', 'https://www.pref.aichi.jp/', None),
        ('pref_police', '愛知県警察', 'https://www.pref.aichi.jp/police/', None),
    ],
    '京都府': [
        ('newspaper', '京都新聞', 'https://www.kyoto-np.co.jp/', None),
        ('tv', 'KBS 京都', 'https://www.kbs-kyoto.co.jp/', None),
        ('pref_gov', '京都府庁', 'https://www.pref.kyoto.jp/', None),
        ('pref_police', '京都府警察', 'https://www.pref.kyoto.jp/fukei/', None),
    ],
    '大阪府': [
        ('newspaper', '産経新聞 大阪本社', 'https://www.sankei.com/west/', None),
        ('newspaper', '朝日新聞 大阪本社', 'https://www.asahi.com/area/osaka/', None),
        ('tv', 'NHK 大阪', 'https://www.nhk.or.jp/osaka/', None),
        ('tv', 'ABC 朝日放送', 'https://www.asahi.co.jp/', None),
        ('pref_gov', '大阪府庁', 'https://www.pref.osaka.lg.jp/', None),
        ('pref_police', '大阪府警察', 'https://www.police.pref.osaka.lg.jp/', None),
    ],
    '兵庫県': [
        ('newspaper', '神戸新聞', 'https://www.kobe-np.co.jp/', None),
        ('tv', 'サンテレビ', 'https://sun-tv.co.jp/', None),
        ('pref_gov', '兵庫県庁', 'https://web.pref.hyogo.lg.jp/', None),
        ('pref_police', '兵庫県警察', 'https://www.police.pref.hyogo.lg.jp/', None),
    ],
    '岡山県': [
        ('newspaper', '山陽新聞', 'https://www.sanyonews.jp/', None),
        ('pref_gov', '岡山県庁', 'https://www.pref.okayama.jp/', None),
        ('pref_police', '岡山県警察', 'https://www.pref.okayama.jp/site/police/', None),
    ],
    '広島県': [
        ('newspaper', '中国新聞', 'https://www.chugoku-np.co.jp/', '中国地方 main 紙'),
        ('tv', '広島ホームテレビ', 'https://www.home-tv.co.jp/', None),
        ('pref_gov', '広島県庁', 'https://www.pref.hiroshima.lg.jp/', None),
        ('pref_police', '広島県警察', 'https://www.pref.hiroshima.lg.jp/site/police/', None),
    ],
    '山口県': [
        ('newspaper', '山口新聞', 'https://www.minato-yamaguchi.co.jp/yama/', None),
        ('newspaper', '中国新聞 山口総局', 'https://www.chugoku-np.co.jp/', None),
        ('pref_gov', '山口県庁', 'https://www.pref.yamaguchi.lg.jp/', None),
        ('pref_police', '山口県警察', 'https://www.police.pref.yamaguchi.jp/', None),
    ],
    '香川県': [
        ('newspaper', '四国新聞', 'https://www.shikoku-np.co.jp/', None),
        ('pref_gov', '香川県庁', 'https://www.pref.kagawa.lg.jp/', None),
        ('pref_police', '香川県警察', 'https://www.pref.kagawa.lg.jp/police/', None),
    ],
    '愛媛県': [
        ('newspaper', '愛媛新聞', 'https://www.ehime-np.co.jp/', None),
        ('pref_gov', '愛媛県庁', 'https://www.pref.ehime.jp/', None),
        ('pref_police', '愛媛県警察', 'https://www.pref.ehime.jp/h25500/', None),
    ],
    '福岡県': [
        ('newspaper', '西日本新聞', 'https://www.nishinippon.co.jp/', '九州 main 紙'),
        ('tv', 'NHK 福岡', 'https://www.nhk.or.jp/fukuoka/', None),
        ('tv', 'FBS 福岡放送', 'https://www.fbs.co.jp/', None),
        ('tv', 'RKB 毎日放送', 'https://rkb.jp/', None),
        ('tv', 'TNC テレビ西日本', 'https://www.tnc.co.jp/', None),
        ('tv', 'KBC 九州朝日放送', 'https://kbc.co.jp/', None),
        ('pref_gov', '福岡県庁', 'https://www.pref.fukuoka.lg.jp/', None),
        ('pref_police', '福岡県警察', 'https://www.police.pref.fukuoka.jp/', None),
        ('bouhai_center', '福岡県暴力追放運動推進センター',
         'https://www.boutsui-fukuoka.or.jp/', None),
    ],
    '佐賀県': [
        ('newspaper', '佐賀新聞', 'https://www.saga-s.co.jp/', None),
        ('tv', 'NHK 佐賀', 'https://www.nhk.or.jp/saga/', None),
        ('pref_gov', '佐賀県庁', 'https://www.pref.saga.lg.jp/', None),
        ('pref_police', '佐賀県警察', 'https://www.pref.saga.lg.jp/police/', None),
    ],
    '長崎県': [
        ('newspaper', '長崎新聞', 'https://nordot.app/-/units/4_nagasaki', None),
        ('tv', 'NBC 長崎放送', 'https://www.nbc-nagasaki.co.jp/', None),
        ('pref_gov', '長崎県庁', 'https://www.pref.nagasaki.jp/', None),
        ('pref_police', '長崎県警察', 'https://www.police.pref.nagasaki.jp/', None),
    ],
    '熊本県': [
        ('newspaper', '熊本日日新聞', 'https://kumanichi.com/', None),
        ('tv', 'NHK 熊本', 'https://www.nhk.or.jp/kumamoto/', None),
        ('tv', 'RKK 熊本放送', 'https://rkk.jp/', None),
        ('pref_gov', '熊本県庁', 'https://www.pref.kumamoto.jp/', None),
        ('pref_police', '熊本県警察', 'https://www.pref.kumamoto.jp/police/', None),
    ],
    '大分県': [
        ('newspaper', '大分合同新聞', 'https://www.oita-press.co.jp/', None),
        ('pref_gov', '大分県庁', 'https://www.pref.oita.jp/', None),
        ('pref_police', '大分県警察', 'https://www.pref.oita.jp/site/police/', None),
    ],
    '宮崎県': [
        ('newspaper', '宮崎日日新聞', 'https://www.the-miyanichi.co.jp/', None),
        ('pref_gov', '宮崎県庁', 'https://www.pref.miyazaki.lg.jp/', None),
        ('pref_police', '宮崎県警察', 'https://www.pref.miyazaki.lg.jp/police/', None),
    ],
    '鹿児島県': [
        ('newspaper', '南日本新聞', 'https://373news.com/', None),
        ('tv', 'MBC 南日本放送', 'https://www.mbc.co.jp/', None),
        ('pref_gov', '鹿児島県庁', 'https://www.pref.kagoshima.jp/', None),
        ('pref_police', '鹿児島県警察', 'https://www.pref.kagoshima.jp/police/', None),
    ],
    '沖縄県': [
        ('newspaper', '沖縄タイムス', 'https://www.okinawatimes.co.jp/', None),
        ('newspaper', '琉球新報', 'https://ryukyushimpo.jp/', None),
        ('tv', 'RBC 琉球放送', 'https://www.rbc.co.jp/', None),
        ('tv', 'OTV 沖縄テレビ', 'https://www.otv.co.jp/', None),
        ('pref_gov', '沖縄県庁', 'https://www.pref.okinawa.lg.jp/', None),
        ('pref_police', '沖縄県警察', 'https://www.police.pref.okinawa.jp/', None),
    ],
}

# 市町村単位の追加情報(主要都市のみ)
CITY_MEDIA = {
    '北九州市': [
        ('city_gov', '北九州市役所', 'https://www.city.kitakyushu.lg.jp/', None),
        ('city_gov', '北九州市市政だより', 'https://www.city.kitakyushu.lg.jp/shisei/', None),
    ],
    '福岡市': [
        ('city_gov', '福岡市役所', 'https://www.city.fukuoka.lg.jp/', None),
    ],
    '神戸市': [
        ('city_gov', '神戸市役所', 'https://www.city.kobe.lg.jp/', None),
    ],
    '広島市': [
        ('city_gov', '広島市役所', 'https://www.city.hiroshima.lg.jp/', None),
    ],
    '札幌市': [
        ('city_gov', '札幌市役所', 'https://www.city.sapporo.jp/', None),
    ],
    '仙台市': [
        ('city_gov', '仙台市役所', 'https://www.city.sendai.jp/', None),
    ],
    '名古屋市': [
        ('city_gov', '名古屋市役所', 'https://www.city.nagoya.jp/', None),
    ],
    '京都市': [
        ('city_gov', '京都市役所', 'https://www.city.kyoto.lg.jp/', None),
    ],
    '大阪市': [
        ('city_gov', '大阪市役所', 'https://www.city.osaka.lg.jp/', None),
    ],
    '那覇市': [
        ('city_gov', '那覇市役所', 'https://www.city.naha.okinawa.jp/', None),
    ],
    '横浜市': [
        ('city_gov', '横浜市役所', 'https://www.city.yokohama.lg.jp/', None),
    ],
    '久留米市': [
        ('city_gov', '久留米市役所', 'https://www.city.kurume.fukuoka.jp/', None),
    ],
    '狛江市': [
        ('city_gov', '狛江市役所', 'https://www.city.komae.tokyo.jp/', None),
    ],
    '浜松市': [
        ('city_gov', '浜松市役所', 'https://www.city.hamamatsu.shizuoka.jp/', None),
    ],
}


# slug → (prefecture, city) — 直接指定があれば優先(自動推定よりも信頼性高)
SLUG_TO_PREFCITY = {
    # 北九州・福岡
    'kudokai_hq_kandake': ('福岡県', '北九州市'),
    'kudokai_hq_kandake_signboard': ('福岡県', '北九州市'),
    'ogura_keisatsu': ('福岡県', '北九州市'),
    'kokurakita_police_station2': ('福岡県', '北九州市'),
    'fukuoka_kenkei': ('福岡県', '北九州市'),
    'kokura_district_court': ('福岡県', '北九州市'),
    'sakaimachi_quarter': ('福岡県', '北九州市'),
    'kyomachi_quarter': ('福岡県', '北九州市'),
    'muromachi_arcade': ('福岡県', '北九州市'),
    'sunatsu_business_area': ('福岡県', '北九州市'),
    'uomachi_arcade': ('福岡県', '北九州市'),
    'tanga_market': ('福岡県', '北九州市'),
    'kokura_station': ('福岡県', '北九州市'),
    'kandake_intersection': ('福岡県', '北九州市'),
    'majaku_district': ('福岡県', '北九州市'),
    'mihagino_district': ('福岡県', '北九州市'),
    'chuocho_center': ('福岡県', '北九州市'),
    'komemachi_arcade': ('福岡県', '北九州市'),
    'uomachi_kawazoi': ('福岡県', '北九州市'),
    'heiwa_dori_street': ('福岡県', '北九州市'),
    'wasshoi_summer_festival': ('福岡県', '北九州市'),
    'horumon_district_sakaimachi': ('福岡県', '北九州市'),
    'kokura_yatai_corner': ('福岡県', '北九州市'),
    'kokuraminami_district': ('福岡県', '北九州市'),
    'kokuraminami_yugawa': ('福岡県', '北九州市'),
    'kokuraminami_tokuriki': ('福岡県', '北九州市'),
    'wakamatsu_takatosan': ('福岡県', '北九州市'),
    'kurosaki_arcade': ('福岡県', '北九州市'),
    'orio_station_area': ('福岡県', '北九州市'),
    'yahatahigashi_kawatamachi': ('福岡県', '北九州市'),
    'yawata_iron_works_area': ('福岡県', '北九州市'),
    'yawata_seitetsu_1901': ('福岡県', '北九州市'),
    'moji_sakaecho': ('福岡県', '北九州市'),
    'mojiport_kitagata_book': ('福岡県', '北九州市'),
    'tobata_yomiya': ('福岡県', '北九州市'),
    'kitakyushu_city_council': ('福岡県', '北九州市'),
    'kokura_bouhai_office': ('福岡県', '北九州市'),
    'kokura_higashi_school': ('福岡県', '北九州市'),
    'kokura_air_raid_1945': ('福岡県', '北九州市'),
    'kokura_yamiichi_1946': ('福岡県', '北九州市'),
    'kusano_ikka_origin_kokura': ('福岡県', '北九州市'),
    'sasashi_udon_first': ('福岡県', '北九州市'),
    'crows_kitakyu_setting': ('福岡県', '北九州市'),
    'attack_2012_ex_officer': ('福岡県', '北九州市'),
    'attack_2013_nurse': ('福岡県', '北九州市'),
    'attack_2014_dentist': ('福岡県', '北九州市'),
    'attack_1998_ashiya_fisheries': ('福岡県', None),
    'heisei_shinten_chi': ('福岡県', '北九州市'),
    'security_guard_attack': ('福岡県', '北九州市'),
    'ex_member_retaliation': ('福岡県', '北九州市'),
    'pachinko_extortion_zone': ('福岡県', '北九州市'),
    'snack_kuyakushotsuki': ('福岡県', '北九州市'),
    'construction_extortion_kitakyushu': ('福岡県', '北九州市'),
    'fukuoka_pref_assembly': ('福岡県', '福岡市'),
    'bouhai_center_fukuoka': ('福岡県', '福岡市'),
    'kasuga_fukuhakukai': ('福岡県', None),
    'yukuhashi_periphery': ('福岡県', None),
    'kanda_industrial': ('福岡県', None),
    'munakata_pref': ('福岡県', None),
    'nogata_bouhai_event': ('福岡県', None),
    'tagawa_taishu_hq': ('福岡県', None),
    'kurume_dojinkai_main_hq': ('福岡県', '久留米市'),
    'kurume_dojinkai_hq': ('福岡県', '久留米市'),
    'kurume_seidokai_hq': ('福岡県', '久留米市'),
    'kurume_namikawakai_hq': ('福岡県', '久留米市'),
    'kurume_bunkagai': ('福岡県', '久留米市'),
    'kurume_bunkagai_central': ('福岡県', '久留米市'),
    'kurume_keisatsu': ('福岡県', '久留米市'),
    'kurume_west_arcade': ('福岡県', '久留米市'),
    'kurume_jr_station': ('福岡県', '久留米市'),
    'kurume_shrine_temple': ('福岡県', '久留米市'),
    'amagi_periphery': ('福岡県', None),
    'omuta_dojin_relation': ('福岡県', None),
    'yamaguchigumi_kyushu_entry': ('福岡県', '北九州市'),
    'tanaka_gumi_offshoot': ('福岡県', '北九州市'),
    'moji_kanmon_line': ('福岡県', '北九州市'),
    'kudogumi_nakatsu_origin': ('大分県', None),
    'nakatsu_kudo_ato': ('大分県', None),
    'fukuoka_robbery_2024': ('福岡県', None),

    # 大分・佐賀・長崎・熊本・宮崎・鹿児島
    'oita_tokuryu': ('大分県', None),
    'saga_periphery_kyushu_war': ('佐賀県', None),
    'saga_periphery_tokuryu': ('佐賀県', None),
    'nagasaki_tokuryu': ('長崎県', None),
    'kumamoto_tokuryu': ('熊本県', None),
    'arao_omuta': ('熊本県', None),  # 荒尾市は熊本
    'miyazaki_tokuryu': ('宮崎県', None),
    'kagoshima_tokuryu': ('鹿児島県', None),

    # 沖縄
    'okinawa_kyokuryukai_main': ('沖縄県', '那覇市'),
    'koza_okinawa': ('沖縄県', None),
    'compare_kyokuryukai_hq': ('沖縄県', '那覇市'),
    'okinawa_us_military_yakuza': ('沖縄県', None),
    'okinawa_tokuryu_serial': ('沖縄県', None),

    # 中国地方
    'hiroshima_kyoseikai_hq': ('広島県', '広島市'),
    'compare_kyoseikai_hq': ('広島県', '広島市'),
    'hiroshima_nagarekawa': ('広島県', '広島市'),
    'hiroshima_atomic_park': ('広島県', '広島市'),
    'hiroshima_keisatsu': ('広島県', '広島市'),
    'hiroshima_yakuza_war': ('広島県', '広島市'),
    'hiroshima_korou_no_chi': ('広島県', '広島市'),
    'hiroshima_jingi_movie': ('広島県', '広島市'),
    'hiroshima_kyoseikai_designation': ('広島県', '広島市'),
    'hiroshima_kyoseikai_offshoots': ('広島県', '広島市'),
    'okayama_tokuryu': ('岡山県', None),
    'yamaguchi_tokuryu': ('山口県', None),

    # 四国
    'takamatsu_marugame': ('香川県', None),
    'kagawa_keisatsu': ('香川県', None),
    'matsuyama_bantencho': ('愛媛県', None),
    'shikoku_yakuza_landscape': ('香川県', None),

    # 北陸
    'niigata_furumachi': ('新潟県', None),
    'niigata_chuetsu_jishin': ('新潟県', None),
    'niigata_robbery_2024': ('新潟県', None),
    'kanazawa_katamachi': ('石川県', None),
    'toyama_keisatsu_area': ('富山県', None),

    # 北海道
    'sapporo_susukino': ('北海道', '札幌市'),
    'hokkaido_keisatsu': ('北海道', '札幌市'),
    'hokkaido_serial_2024': ('北海道', None),
    'hakodate_chinatown': ('北海道', None),
    'otaru_yakuza_history': ('北海道', None),

    # 東北
    'sendai_kokubun': ('宮城県', '仙台市'),
    'sendai_station_area': ('宮城県', '仙台市'),
    'miyagi_keisatsu': ('宮城県', '仙台市'),
    'koriyama_fukushima_renge': ('福島県', None),
    'fukushima_keisatsu': ('福島県', None),
    'disaster_311_yakuza_response': ('宮城県', '仙台市'),

    # 関東
    'roppongi_clubs_hangure': ('東京都', None),
    'roppongi_flower_attack': ('東京都', None),
    'shinjuku_chaika_hangure': ('東京都', None),
    'shibuya_halloween_arrest': ('東京都', None),
    'tokyo_kabukicho': ('東京都', None),
    'tokyo_kabukicho_east_tower': ('東京都', None),
    'tokyo_shibuya_yakuza': ('東京都', None),
    'tokyo_yakuzas_hubs': ('東京都', None),
    'tokyo_finance_district': ('東京都', None),
    'tokyo_sumiyoshi_hq': ('東京都', None),
    'tokyo_inagawakai_hq': ('東京都', None),
    'tokyo_npa_hq': ('東京都', None),
    'tokyo_metro_keisatsu': ('東京都', None),
    'tokyo_fsa': ('東京都', None),
    'tokyo_diet_again': ('東京都', None),
    'tokyo_us_embassy': ('東京都', None),
    'mizuho_bank_hq': ('東京都', None),
    'zenginkyo_compliance': ('東京都', None),
    'compare_sumiyoshi_hq': ('東京都', None),
    'compare_inagawakai_hq': ('東京都', None),
    'compare_kyokutokai_hq': ('東京都', None),
    'kanto_rengo_hq': ('東京都', None),
    'kanto_rengo_ob_network': ('東京都', None),
    'doragon_chinese_hangure': ('東京都', None),
    'npa_tokuryu_office': ('東京都', None),
    'npa_tokuryu_analysis_room': ('東京都', None),
    'mpd_tokuryu_specialist': ('東京都', None),
    'undercover_yamiarbeit': ('東京都', None),
    'crypto_mixing_takedown_2025': ('東京都', None),
    'account_provider_takedown_2025': ('東京都', None),
    'fukuchi_yamiarbeit_trial': ('東京都', None),
    'shutoken_serial_2024': ('東京都', None),
    'tokyo_sns_recruiter_office': ('東京都', None),
    'shinagawa_yamiarbeit_2024': ('東京都', None),
    'komae_robbery_2023': ('東京都', '狛江市'),
    'inagi_robbery_2022': ('東京都', None),
    # Phase 52 chaos sites
    'yakiudon_origin': ('福岡県', '北九州市'),
    'moji_yaki_curry': ('福岡県', '北九州市'),
    'nukadakimoto': ('福岡県', '北九州市'),
    'giravanz_kitakyushu': ('福岡県', '北九州市'),
    'kitakyushu_medi_dome': ('福岡県', '北九州市'),
    'boatrace_wakamatsu': ('福岡県', '北九州市'),
    'kitakyushu_zoo': ('福岡県', '北九州市'),
    'kokura_jigon_drum': ('福岡県', '北九州市'),
    'tobata_giant_yamagasa': ('福岡県', '北九州市'),
    'yawata_matsuri': ('福岡県', '北九州市'),
    'takakura_ken_birthplace': ('福岡県', None),
    'matsumoto_leiji_birthplace': ('福岡県', '北九州市'),
    'hojo_tsukasa_birthplace': ('福岡県', '北九州市'),
    'robert_akiyama_birthplace': ('福岡県', '北九州市'),
    'suzuki_kosuke_birthplace': ('福岡県', '北九州市'),
    'uomachi_chinese_chinatown': ('福岡県', '北九州市'),
    'kitakyushu_mahjong_culture': ('福岡県', '北九州市'),
    'compound_time_machine_sister': (None, None),  # 海外プロジェクト
    'kokkai_diet_tokyo': ('東京都', None),
    'kodama_yoshio_residence': ('東京都', None),
    'iranian_dealers_shibuya': ('東京都', None),
    'dangerous_drugs_zone': ('東京都', None),
    'hangure_tokuryu_origin_culture': ('東京都', None),
    'luffy_court_proceedings': ('東京都', None),
    'luffy_satsumitsu_court': ('東京都', None),
    'tokuryu_recruiter_takedown': ('東京都', None),
    'atm_uketakedashi_arrests': ('東京都', None),
    'school_predator_warning': ('東京都', None),
    'ulu_atm_demand': ('東京都', None),
    'kabuki_jingi_movie': ('東京都', None),
    'ryugagotoku_virtual': ('東京都', None),

    'hangure_yokohama_chinatown': ('神奈川県', '横浜市'),
    'kanagawa_yokohama_robbery': ('神奈川県', '横浜市'),
    'chiba_isumi_robbery': ('千葉県', None),
    'saitama_warabi_robbery': ('埼玉県', None),
    'ibaraki_chikusei_robbery': ('茨城県', None),
    'tochigi_oyama_robbery': ('栃木県', None),
    'takasaki_gunma_robbery': ('群馬県', None),
    'drug_meth_2019_yokohama': ('神奈川県', '横浜市'),

    # 関西
    'kobe_yamaguchi_souhonbu': ('兵庫県', '神戸市'),
    'kobe_yamaguchi_origin': ('兵庫県', '神戸市'),
    'kobe_geinosha': ('兵庫県', '神戸市'),
    'kobe_kobeyamaguchigumi_hq': ('兵庫県', '神戸市'),
    'kobe_kizunakai_hq': ('兵庫県', '神戸市'),
    'kobe_yamaichi_ground_zero': ('兵庫県', '神戸市'),
    'hyogo_keisatsu_hq': ('兵庫県', '神戸市'),
    'shinobu_tsukasa_kobe': ('兵庫県', '神戸市'),
    'compare_yamaguchigumi_hq': ('兵庫県', '神戸市'),
    'kansai_quake_yamaguchi': ('兵庫県', '神戸市'),
    'hyogo_robbery_2024': ('兵庫県', '神戸市'),

    'osaka_yamaguchi_kizunabashi': ('大阪府', '大阪市'),
    'osaka_minami_yakuza': ('大阪府', '大阪市'),
    'osaka_kita_yakuza': ('大阪府', '大阪市'),
    'osaka_kamagasaki': ('大阪府', '大阪市'),
    'osaka_robbery_tokuryu': ('大阪府', '大阪市'),
    'osaka_sns_recruiter': ('大阪府', '大阪市'),
    'osaka_serial_2024': ('大阪府', '大阪市'),

    'kyoto_aizukotetsu_hq': ('京都府', '京都市'),
    'kyoto_gion': ('京都府', '京都市'),
    'compare_aizukotetsu_hq': ('京都府', '京都市'),
    'compare_kyokuseikai_hq': ('広島県', '広島市'),
    'compare_namikawakai_hq': ('福岡県', '久留米市'),
    'kyoto_jewelry_robbery': ('京都府', '京都市'),

    # 名古屋・中部
    'nagoya_kodokai_hq': ('愛知県', '名古屋市'),
    'nagoya_sakae_district': ('愛知県', '名古屋市'),
    'aichi_nagoya_robbery': ('愛知県', '名古屋市'),

    # 静岡
    'hamamatsu_kasai_visit': ('静岡県', '浜松市'),
    'shizuoka_kenkei_drills': ('静岡県', None),

    # 国際拠点(海外)= 地元メディアなし(国別の主要メディアは別途定義)
    'philippines_luffy_base': (None, None),
    'cambodia_compounds_link': (None, None),
    'myanmar_compounds_link': (None, None),
    'thailand_tokuryu_base': (None, None),
    'vietnam_tokuryu_base': (None, None),
    'laos_tokuryu_base': (None, None),
    'tokuryu_kankoku_link': (None, None),
    'drug_korea_route': (None, None),
    'drug_china_southeast': (None, None),
    'intl_cosa_nostra_italy': (None, None),
    'intl_ndrangheta_italy': (None, None),
    'intl_triads_hk': (None, None),
    'intl_la_cosa_nostra_us': (None, None),
    'intl_mekong_compounds_ref': (None, None),
    'roman_sagi_centers': (None, None),

    # 全国・抽象
    'kinpaku_strong_22pref': (None, None),
    'hakusho_2024_arrests_10k': ('東京都', None),  # 警察白書本庁
    'drug_smuggling_routes': (None, None),
    'drug_busts_1990s': (None, None),
    'drug_2020s_busts': (None, None),
    'drug_telegram_market': (None, None),
    'special_fraud_callcenter': (None, None),
    'roman_sagi_online': (None, None),
    'telegram_yamiarbeit': (None, None),
    'tokuryu_crypto_laundering': (None, None),
    'tokuryu_young_recruits': (None, None),
    'tokuryu_pawn_jewelry_route': (None, None),
    'jr_route_robbery_2024': (None, None),
    'ofac_treasury_designation': ('東京都', None),
    'ex_yakuza_to_tokuryu': (None, None),
    'hiropon_first_wave': (None, None),
    'hiropon_second_wave': (None, None),
    'cannabis_route_history': (None, None),
    'honda_kai_war': ('兵庫県', '神戸市'),
    'postwar_sanguokujin': (None, None),
    'koshienjo_yakuza': ('兵庫県', None),
    'misora_hibari_taoka': ('兵庫県', '神戸市'),
    'lockheed_scandal': ('東京都', None),
    'bubble_jiage': ('東京都', None),
    'jusen_jutaku': ('東京都', None),
    'proyakyu_kuroikiri': ('東京都', None),
    'sumo_yakyu_baqto': ('東京都', None),
    'sumo_yaocho_2011': ('東京都', None),
    'magazine_tsukuru': ('東京都', None),
    'jitsuwa_magazines': ('東京都', None),
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    # Create table
    cur.execute('''
      CREATE TABLE IF NOT EXISTS local_media (
        id INTEGER PRIMARY KEY,
        site_id INTEGER NOT NULL,
        kind TEXT,
        name TEXT NOT NULL,
        url TEXT,
        note TEXT,
        ord INTEGER DEFAULT 100,
        FOREIGN KEY (site_id) REFERENCES site(id)
      )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_local_media_site ON local_media(site_id)')
    cur.execute('DELETE FROM local_media')  # full rebuild

    sites = cur.execute('SELECT id, slug FROM site').fetchall()
    inserted = 0; assigned = 0; orphan = []
    for sid, slug in sites:
        info = SLUG_TO_PREFCITY.get(slug)
        if info is None:
            orphan.append(slug); continue
        pref, city = info
        if pref is None and city is None:
            continue  # 海外・抽象拠点 = 地元メディアなし
        assigned += 1
        ord_ = 10
        if pref and pref in LOCAL_MEDIA_BY_PREF:
            for kind, name, url, note in LOCAL_MEDIA_BY_PREF[pref]:
                cur.execute('INSERT INTO local_media(site_id, kind, name, url, note, ord) '
                            'VALUES (?,?,?,?,?,?)',
                            (sid, kind, name, url, note, ord_))
                ord_ += 5
                inserted += 1
        if city and city in CITY_MEDIA:
            for kind, name, url, note in CITY_MEDIA[city]:
                cur.execute('INSERT INTO local_media(site_id, kind, name, url, note, ord) '
                            'VALUES (?,?,?,?,?,?)',
                            (sid, kind, name, url, note, ord_))
                ord_ += 5
                inserted += 1

    con.commit()
    print(f'phase46_local_media: {inserted} rows inserted across {assigned} sites')
    if orphan:
        print(f'  WARN: {len(orphan)} sites unmapped (need SLUG_TO_PREFCITY entry):')
        for o in orphan[:30]: print(f'    - {o}')
        if len(orphan) > 30: print(f'    ... and {len(orphan)-30} more')
    con.close()


if __name__ == '__main__':
    main()
