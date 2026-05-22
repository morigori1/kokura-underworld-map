"""Phase 48: 都市・区レベルの地元メディアを大幅追加 + tier 階層化。

ユーザー要望「地元の都市ベースがいいんだよな」に応える。

変更:
  - local_media に tier 列追加(city / pref / national / intl)
  - 既存エントリの tier を kind から自動推定
  - 主要都市・区・町に細かい地元メディア(市政だより・警察署・
    暴追地区・地元 FM・商工会議所)を追加
  - 表示は tier 順に並べ替える(都市 > 県 > 国 > 国際)

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


# 都市・区レベルの追加情報
# 主要都市: 北九州 / 福岡 / 久留米 / 神戸 / 大阪 / 京都 / 名古屋 / 東京23区 /
# 横浜 / 札幌 / 仙台 / 那覇 / その他

# city/ward name → [(kind, name, url, note)]
CITY_DETAIL = {
    # ===== 北九州市 各区 =====
    '北九州市': [
        ('city_gov', '北九州市役所', 'https://www.city.kitakyushu.lg.jp/', None),
        ('city_gov', '北九州市政だより', 'https://www.city.kitakyushu.lg.jp/shisei/k0500001.html',
         '市の広報誌'),
        ('city_gov', '北九州市暴追運動推進会議事務局',
         'https://www.city.kitakyushu.lg.jp/', '市庁内事務局'),
        ('npo', '北九州商工会議所', 'https://www.kitakyushucci.or.jp/',
         '事業者向け暴排講習を継続開催'),
        ('radio', 'FM KITAQ(エフエム北九州)',
         'https://fmkitaq.com/', '地元コミュニティ FM'),
        ('library', '北九州市立中央図書館',
         'https://www.city.kitakyushu.lg.jp/kyouiku/k1500001.html', None),
        ('museum', 'いのちのたび博物館',
         'https://www.kmnh.jp/', '北九州自然史・歴史博物館'),
    ],

    # 北九州 — 区別 (区役所 + 区内警察署 / 区内主要施設)
    '北九州市小倉北区': [
        ('city_gov', '小倉北区役所', 'https://www.city.kitakyushu.lg.jp/kokurakita/', None),
        ('pref_police', '小倉北警察署',
         'https://www.police.pref.fukuoka.jp/kokurakita/', '神岳1-3-3'),
    ],
    '北九州市小倉南区': [
        ('city_gov', '小倉南区役所', 'https://www.city.kitakyushu.lg.jp/kokuraminami/', None),
        ('pref_police', '小倉南警察署',
         'https://www.police.pref.fukuoka.jp/kokuraminami/', None),
    ],
    '北九州市八幡東区': [
        ('city_gov', '八幡東区役所', 'https://www.city.kitakyushu.lg.jp/yahatahigashi/', None),
        ('pref_police', '八幡東警察署',
         'https://www.police.pref.fukuoka.jp/yahatahigashi/', None),
    ],
    '北九州市八幡西区': [
        ('city_gov', '八幡西区役所', 'https://www.city.kitakyushu.lg.jp/yahatanishi/', None),
        ('pref_police', '八幡西警察署',
         'https://www.police.pref.fukuoka.jp/yahatanishi/', None),
    ],
    '北九州市門司区': [
        ('city_gov', '門司区役所', 'https://www.city.kitakyushu.lg.jp/moji/', None),
        ('pref_police', '門司警察署',
         'https://www.police.pref.fukuoka.jp/moji/', None),
        ('museum', '門司港レトロ', 'https://www.mojiko.info/',
         '門司港観光振興'),
    ],
    '北九州市戸畑区': [
        ('city_gov', '戸畑区役所', 'https://www.city.kitakyushu.lg.jp/tobata/', None),
        ('pref_police', '戸畑警察署',
         'https://www.police.pref.fukuoka.jp/tobata/', None),
    ],
    '北九州市若松区': [
        ('city_gov', '若松区役所', 'https://www.city.kitakyushu.lg.jp/wakamatsu/', None),
        ('pref_police', '若松警察署',
         'https://www.police.pref.fukuoka.jp/wakamatsu/', None),
    ],

    # 福岡市
    '福岡市': [
        ('city_gov', '福岡市役所', 'https://www.city.fukuoka.lg.jp/', None),
        ('city_gov', '福岡市政だより', 'https://www.city.fukuoka.lg.jp/data/open/cnt/3/164/1/',
         None),
        ('radio', 'LOVE FM', 'https://lovefm.co.jp/', '福岡国際 FM'),
        ('radio', 'FM FUKUOKA', 'https://fmfukuoka.co.jp/', None),
    ],

    # 久留米市
    '久留米市': [
        ('city_gov', '久留米市役所', 'https://www.city.kurume.fukuoka.jp/', None),
        ('city_gov', '広報くるめ',
         'https://www.city.kurume.fukuoka.jp/site/koho-kurume/', None),
        ('pref_police', '久留米警察署',
         'https://www.police.pref.fukuoka.jp/kurume/', None),
        ('radio', 'ドリームスFM',
         'https://www.dreamsfm.co.jp/', '久留米地域コミュニティ FM'),
    ],

    # 大牟田・荒尾
    '大牟田市': [
        ('city_gov', '大牟田市役所', 'https://www.city.omuta.lg.jp/', None),
        ('pref_police', '大牟田警察署',
         'https://www.police.pref.fukuoka.jp/omuta/', None),
    ],

    # 田川市
    '田川市': [
        ('city_gov', '田川市役所', 'https://www.city.tagawa.lg.jp/', None),
        ('pref_police', '田川警察署',
         'https://www.police.pref.fukuoka.jp/tagawa/', None),
    ],

    # 直方市
    '直方市': [
        ('city_gov', '直方市役所', 'https://www.city.nogata.fukuoka.jp/', None),
    ],

    # 行橋市
    '行橋市': [
        ('city_gov', '行橋市役所', 'https://www.city.yukuhashi.fukuoka.jp/', None),
    ],

    # 中津市(大分)
    '中津市': [
        ('city_gov', '中津市役所', 'https://www.city-nakatsu.jp/', None),
        ('pref_police', '中津警察署',
         'https://www.pref.oita.jp/site/police/', None),
    ],

    # ===== 神戸市 各区 =====
    '神戸市': [
        ('city_gov', '神戸市役所', 'https://www.city.kobe.lg.jp/', None),
        ('city_gov', '広報こうべ', 'https://www.city.kobe.lg.jp/a08576/shise/kohokocho/koho/',
         None),
        ('radio', 'Kiss FM KOBE', 'https://www.kiss-fm.co.jp/',
         '神戸ラジオ局'),
    ],
    '神戸市灘区': [
        ('city_gov', '灘区役所', 'https://www.city.kobe.lg.jp/a89177/kuyakusho/nadaku/', None),
        ('pref_police', '灘警察署',
         'https://www.police.pref.hyogo.lg.jp/nada/', None),
    ],
    '神戸市中央区': [
        ('city_gov', '中央区役所', 'https://www.city.kobe.lg.jp/a89177/kuyakusho/chuoku/', None),
        ('pref_police', '葺合警察署',
         'https://www.police.pref.hyogo.lg.jp/fukiai/', '神戸市中央区東部'),
        ('pref_police', '生田警察署',
         'https://www.police.pref.hyogo.lg.jp/ikuta/', '神戸市中央区西部'),
    ],
    '神戸市東灘区': [
        ('city_gov', '東灘区役所', 'https://www.city.kobe.lg.jp/a89177/kuyakusho/higashinadaku/', None),
        ('pref_police', '東灘警察署',
         'https://www.police.pref.hyogo.lg.jp/higashinada/', None),
    ],

    # 淡路市(神戸山口組本部)
    '淡路市': [
        ('city_gov', '淡路市役所', 'https://www.city.awaji.lg.jp/', None),
        ('pref_police', '淡路警察署',
         'https://www.police.pref.hyogo.lg.jp/awaji/', None),
    ],

    # ===== 大阪市 各区 =====
    '大阪市': [
        ('city_gov', '大阪市役所', 'https://www.city.osaka.lg.jp/', None),
        ('radio', 'FM802', 'https://funky802.com/', '大阪 FM 局'),
        ('radio', 'MBS ラジオ', 'https://www.mbs1179.com/', None),
    ],
    '大阪市中央区': [
        ('city_gov', '中央区役所', 'https://www.city.osaka.lg.jp/chuo/', None),
        ('pref_police', '南警察署',
         'https://www.police.pref.osaka.lg.jp/minami/', 'ミナミ・道頓堀担当'),
    ],
    '大阪市北区': [
        ('city_gov', '北区役所', 'https://www.city.osaka.lg.jp/kita/', None),
        ('pref_police', '曽根崎警察署',
         'https://www.police.pref.osaka.lg.jp/sonezaki/', '北新地担当'),
    ],
    '大阪市西成区': [
        ('city_gov', '西成区役所', 'https://www.city.osaka.lg.jp/nishinari/', None),
        ('pref_police', '西成警察署',
         'https://www.police.pref.osaka.lg.jp/nishinari/', '釜ヶ崎・あいりん地区担当'),
    ],

    # 京都市
    '京都市': [
        ('city_gov', '京都市役所', 'https://www.city.kyoto.lg.jp/', None),
        ('radio', 'α-STATION FM京都',
         'https://fm-kyoto.jp/', None),
    ],
    '京都市下京区': [
        ('city_gov', '下京区役所', 'https://www.city.kyoto.lg.jp/shimogyo/', None),
        ('pref_police', '下京警察署',
         'https://www.pref.kyoto.jp/fukei/index_kabu_index.html', None),
    ],
    '京都市東山区': [
        ('city_gov', '東山区役所', 'https://www.city.kyoto.lg.jp/higashiyama/', None),
        ('pref_police', '東山警察署', 'https://www.pref.kyoto.jp/fukei/', '祇園・清水寺担当'),
    ],

    # 名古屋市
    '名古屋市': [
        ('city_gov', '名古屋市役所', 'https://www.city.nagoya.jp/', None),
        ('radio', 'FM AICHI', 'https://www.fma.co.jp/', None),
    ],
    '名古屋市中区': [
        ('city_gov', '中区役所', 'https://www.city.nagoya.jp/naka/', None),
        ('pref_police', '中警察署',
         'https://www.pref.aichi.jp/police/naka/', '栄担当'),
    ],

    # ===== 東京都 主要区 =====
    '港区': [
        ('city_gov', '港区役所', 'https://www.city.minato.tokyo.jp/', None),
        ('pref_police', '麻布警察署',
         'https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_johvedrooku/jokyo/azabu.html',
         '六本木担当'),
        ('pref_police', '赤坂警察署',
         'https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_johvedrooku/jokyo/akasaka.html',
         '赤坂・住吉会本部周辺担当'),
        ('pref_police', '高輪警察署',
         'https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_johvedrooku/jokyo/takanawa.html',
         '高輪・品川北部'),
    ],
    '新宿区': [
        ('city_gov', '新宿区役所', 'https://www.city.shinjuku.lg.jp/', None),
        ('pref_police', '新宿警察署',
         'https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_johvedrooku/jokyo/shinjuku.html',
         '歌舞伎町担当'),
    ],
    '渋谷区': [
        ('city_gov', '渋谷区役所', 'https://www.city.shibuya.tokyo.jp/', None),
        ('pref_police', '渋谷警察署',
         'https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_johvedrooku/jokyo/shibuya.html',
         '渋谷ハロウィン警備の主担当'),
    ],
    '千代田区': [
        ('city_gov', '千代田区役所', 'https://www.city.chiyoda.lg.jp/', None),
        ('pref_police', '丸の内警察署',
         'https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_johvedrooku/jokyo/marunouchi.html',
         '丸の内・大手町担当'),
    ],
    '江戸川区': [
        ('city_gov', '江戸川区役所', 'https://www.city.edogawa.tokyo.jp/', None),
        ('pref_police', '小松川警察署',
         'https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_johvedrooku/jokyo/komatsugawa.html',
         '怒羅権発祥地周辺担当'),
    ],

    # 狛江市
    '狛江市': [
        ('city_gov', '狛江市役所', 'https://www.city.komae.tokyo.jp/', None),
        ('pref_police', '調布警察署',
         'https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_johvedrooku/jokyo/chofu.html',
         '狛江・調布担当'),
    ],

    # 横浜・川崎
    '横浜市': [
        ('city_gov', '横浜市役所', 'https://www.city.yokohama.lg.jp/', None),
        ('radio', 'FM Yokohama', 'https://www.fmyokohama.co.jp/', None),
    ],
    '横浜市中区': [
        ('city_gov', '中区役所', 'https://www.city.yokohama.lg.jp/naka/', None),
        ('pref_police', '加賀町警察署',
         'https://www.police.pref.kanagawa.jp/ps/55ps/index.htm',
         '横浜中華街担当'),
    ],

    # 北海道・札幌
    '札幌市': [
        ('city_gov', '札幌市役所', 'https://www.city.sapporo.jp/', None),
        ('radio', 'AIR-G\' FM北海道', 'https://www.air-g.co.jp/', None),
    ],
    '札幌市中央区': [
        ('city_gov', '中央区役所', 'https://www.city.sapporo.jp/chuo/', None),
        ('pref_police', 'すすきの・中央警察署',
         'https://www.police.pref.hokkaido.lg.jp/', 'すすきの担当'),
    ],

    # 函館・小樽
    '函館市': [
        ('city_gov', '函館市役所', 'https://www.city.hakodate.hokkaido.jp/', None),
        ('newspaper', '函館新聞', 'https://digital.hakoshin.jp/', None),
    ],
    '小樽市': [
        ('city_gov', '小樽市役所', 'https://www.city.otaru.lg.jp/', None),
    ],

    # 東北
    '仙台市': [
        ('city_gov', '仙台市役所', 'https://www.city.sendai.jp/', None),
        ('radio', 'FM 仙台 Date fm', 'https://www.datefm.co.jp/', None),
    ],
    '仙台市青葉区': [
        ('city_gov', '青葉区役所', 'https://www.city.sendai.jp/aoba-shimin/', None),
        ('pref_police', '仙台中央警察署',
         'https://www.police.pref.miyagi.jp/', '国分町担当'),
    ],
    '郡山市': [
        ('city_gov', '郡山市役所', 'https://www.city.koriyama.lg.jp/', None),
    ],
    '福島市': [
        ('city_gov', '福島市役所', 'https://www.city.fukushima.fukushima.jp/', None),
    ],

    # 四国
    '高松市': [
        ('city_gov', '高松市役所', 'https://www.city.takamatsu.kagawa.jp/', None),
        ('pref_police', '高松北警察署',
         'https://www.pref.kagawa.lg.jp/police/', '丸亀町担当'),
    ],
    '松山市': [
        ('city_gov', '松山市役所', 'https://www.city.matsuyama.ehime.jp/', None),
    ],

    # 北陸
    '新潟市': [
        ('city_gov', '新潟市役所', 'https://www.city.niigata.lg.jp/', None),
    ],
    '金沢市': [
        ('city_gov', '金沢市役所', 'https://www4.city.kanazawa.lg.jp/', None),
    ],

    # 静岡
    '浜松市': [
        ('city_gov', '浜松市役所', 'https://www.city.hamamatsu.shizuoka.jp/', None),
        ('newspaper', '中日新聞 浜松総局',
         'https://www.chunichi.co.jp/area/shizuoka/hamamatsu/',
         '中日新聞 浜松エリア版'),
        ('radio', 'FM Haro!', 'https://www.fmharo.co.jp/',
         '浜松コミュニティ FM'),
    ],
    '静岡市': [
        ('city_gov', '静岡市役所', 'https://www.city.shizuoka.lg.jp/', None),
    ],

    # 九州各県
    '佐賀市': [
        ('city_gov', '佐賀市役所', 'https://www.city.saga.lg.jp/', None),
    ],
    '長崎市': [
        ('city_gov', '長崎市役所', 'https://www.city.nagasaki.lg.jp/', None),
    ],
    '熊本市': [
        ('city_gov', '熊本市役所', 'https://www.city.kumamoto.jp/', None),
        ('radio', 'FM Kumamoto', 'https://www.fmk.fm/', None),
    ],
    '宮崎市': [
        ('city_gov', '宮崎市役所', 'https://www.city.miyazaki.miyazaki.jp/', None),
    ],
    '鹿児島市': [
        ('city_gov', '鹿児島市役所', 'https://www.city.kagoshima.lg.jp/', None),
        ('radio', 'μFM', 'https://www.myufm.jp/', None),
    ],
    '大分市': [
        ('city_gov', '大分市役所', 'https://www.city.oita.oita.jp/', None),
    ],
    '岡山市': [
        ('city_gov', '岡山市役所', 'https://www.city.okayama.jp/', None),
    ],

    # 沖縄
    '那覇市': [
        ('city_gov', '那覇市役所', 'https://www.city.naha.okinawa.jp/', None),
        ('radio', 'FM那覇', 'https://www.fmnaha.jp/', None),
    ],
    '沖縄市': [
        ('city_gov', '沖縄市役所', 'https://www.city.okinawa.okinawa.jp/', None),
    ],
}

# slug → city/ward name (細かい指定が必要なものは追加マッピング)
SLUG_TO_CITYWARD_DETAIL = {
    # 北九州 区別
    'kudokai_hq_kandake': '北九州市小倉北区',
    'kudokai_hq_kandake_signboard': '北九州市小倉北区',
    'ogura_keisatsu': '北九州市小倉北区',
    'kokurakita_police_station2': '北九州市小倉北区',
    'fukuoka_kenkei': '北九州市小倉北区',
    'kokura_district_court': '北九州市小倉北区',
    'sakaimachi_quarter': '北九州市小倉北区',
    'kyomachi_quarter': '北九州市小倉北区',
    'muromachi_arcade': '北九州市小倉北区',
    'sunatsu_business_area': '北九州市小倉北区',
    'uomachi_arcade': '北九州市小倉北区',
    'tanga_market': '北九州市小倉北区',
    'kokura_station': '北九州市小倉北区',
    'kandake_intersection': '北九州市小倉北区',
    'majaku_district': '北九州市小倉北区',
    'mihagino_district': '北九州市小倉北区',
    'chuocho_center': '北九州市小倉北区',
    'komemachi_arcade': '北九州市小倉北区',
    'uomachi_kawazoi': '北九州市小倉北区',
    'heiwa_dori_street': '北九州市小倉北区',
    'wasshoi_summer_festival': '北九州市小倉北区',
    'horumon_district_sakaimachi': '北九州市小倉北区',
    'kokura_yatai_corner': '北九州市小倉北区',
    'kokuraminami_district': '北九州市小倉南区',
    'kokuraminami_yugawa': '北九州市小倉南区',
    'kokuraminami_tokuriki': '北九州市小倉南区',
    'sasashi_udon_first': '北九州市小倉南区',
    'wakamatsu_takatosan': '北九州市若松区',
    'kurosaki_arcade': '北九州市八幡西区',
    'orio_station_area': '北九州市八幡西区',
    'yahatahigashi_kawatamachi': '北九州市八幡東区',
    'yawata_iron_works_area': '北九州市八幡東区',
    'yawata_seitetsu_1901': '北九州市八幡東区',
    'moji_sakaecho': '北九州市門司区',
    'mojiport_kitagata_book': '北九州市門司区',
    'tobata_yomiya': '北九州市戸畑区',
    'kitakyushu_city_council': '北九州市小倉北区',
    'kokura_bouhai_office': '北九州市小倉北区',
    'kokura_higashi_school': '北九州市小倉北区',
    'kokura_air_raid_1945': '北九州市小倉北区',
    'kokura_yamiichi_1946': '北九州市小倉北区',
    'kusano_ikka_origin_kokura': '北九州市小倉北区',
    'attack_2012_ex_officer': '北九州市小倉北区',
    'attack_2013_nurse': '北九州市小倉北区',
    'attack_2014_dentist': '北九州市小倉北区',
    'heisei_shinten_chi': '北九州市小倉北区',
    'security_guard_attack': '北九州市小倉北区',
    'ex_member_retaliation': '北九州市小倉北区',
    'pachinko_extortion_zone': '北九州市',
    'snack_kuyakushotsuki': '北九州市小倉北区',
    'construction_extortion_kitakyushu': '北九州市',
    'crows_kitakyu_setting': '北九州市',
    'moji_kanmon_line': '北九州市門司区',
    'tanaka_gumi_offshoot': '北九州市',
    'yamaguchigumi_kyushu_entry': '北九州市',
    # 大分中津
    'kudogumi_nakatsu_origin': '中津市',
    'nakatsu_kudo_ato': '中津市',
    # 大牟田/田川/直方/行橋
    'omuta_dojin_relation': '大牟田市',
    'arao_omuta': '大牟田市',
    'tagawa_taishu_hq': '田川市',
    'nogata_bouhai_event': '直方市',
    'yukuhashi_periphery': '行橋市',
    # 神戸 区別
    'kobe_yamaguchi_souhonbu': '神戸市灘区',
    'kobe_yamaguchi_origin': '神戸市中央区',
    'kobe_geinosha': '神戸市灘区',
    'kobe_kobeyamaguchigumi_hq': '淡路市',
    'kobe_kizunakai_hq': '神戸市中央区',
    'kobe_yamaichi_ground_zero': '神戸市東灘区',
    'hyogo_keisatsu_hq': '神戸市中央区',
    'shinobu_tsukasa_kobe': '神戸市灘区',
    'compare_yamaguchigumi_hq': '神戸市灘区',
    'kansai_quake_yamaguchi': '神戸市灘区',
    'misora_hibari_taoka': '神戸市灘区',
    'honda_kai_war': '神戸市',
    # 大阪 区別
    'osaka_minami_yakuza': '大阪市中央区',
    'osaka_kita_yakuza': '大阪市北区',
    'osaka_kamagasaki': '大阪市西成区',
    'osaka_yamaguchi_kizunabashi': '大阪市',
    'osaka_robbery_tokuryu': '大阪市',
    'osaka_sns_recruiter': '大阪市',
    'osaka_serial_2024': '大阪市',
    # 京都 区別
    'kyoto_aizukotetsu_hq': '京都市下京区',
    'kyoto_gion': '京都市東山区',
    'compare_aizukotetsu_hq': '京都市下京区',
    'kyoto_jewelry_robbery': '京都市',
    # 名古屋 区別
    'nagoya_kodokai_hq': '名古屋市中区',
    'nagoya_sakae_district': '名古屋市中区',
    'aichi_nagoya_robbery': '名古屋市',
    # 東京 区別
    'roppongi_clubs_hangure': '港区',
    'roppongi_flower_attack': '港区',
    'tokyo_sumiyoshi_hq': '港区',
    'tokyo_inagawakai_hq': '港区',
    'compare_sumiyoshi_hq': '港区',
    'compare_inagawakai_hq': '港区',
    'kodama_yoshio_residence': '港区',
    'tokyo_us_embassy': '港区',
    'shinjuku_chaika_hangure': '新宿区',
    'tokyo_kabukicho': '新宿区',
    'shibuya_halloween_arrest': '渋谷区',
    'tokyo_shibuya_yakuza': '渋谷区',
    'iranian_dealers_shibuya': '渋谷区',
    'dangerous_drugs_zone': '渋谷区',
    'tokyo_npa_hq': '千代田区',
    'tokyo_metro_keisatsu': '千代田区',
    'tokyo_fsa': '千代田区',
    'tokyo_diet_again': '千代田区',
    'kokkai_diet_tokyo': '千代田区',
    'tokyo_finance_district': '千代田区',
    'mizuho_bank_hq': '千代田区',
    'zenginkyo_compliance': '千代田区',
    'doragon_chinese_hangure': '江戸川区',
    'npa_tokuryu_office': '千代田区',
    'npa_tokuryu_analysis_room': '千代田区',
    'mpd_tokuryu_specialist': '千代田区',
    'undercover_yamiarbeit': '千代田区',
    'crypto_mixing_takedown_2025': '千代田区',
    'account_provider_takedown_2025': '千代田区',
    'fukuchi_yamiarbeit_trial': '千代田区',
    'luffy_court_proceedings': '千代田区',
    'luffy_satsumitsu_court': '千代田区',
    'tokuryu_recruiter_takedown': '千代田区',
    'hakusho_2024_arrests_10k': '千代田区',
    'ofac_treasury_designation': '港区',  # 米国大使館近接
    'komae_robbery_2023': '狛江市',
    'inagi_robbery_2022': '東京都',
    # 横浜
    'hangure_yokohama_chinatown': '横浜市中区',
    'kanagawa_yokohama_robbery': '横浜市',
    'drug_meth_2019_yokohama': '横浜市中区',
    # 北海道
    'sapporo_susukino': '札幌市中央区',
    'hokkaido_keisatsu': '札幌市中央区',
    'hokkaido_serial_2024': '札幌市',
    'hakodate_chinatown': '函館市',
    'otaru_yakuza_history': '小樽市',
    # 東北
    'sendai_kokubun': '仙台市青葉区',
    'sendai_station_area': '仙台市青葉区',
    'miyagi_keisatsu': '仙台市青葉区',
    'koriyama_fukushima_renge': '郡山市',
    'fukushima_keisatsu': '福島市',
    'disaster_311_yakuza_response': '仙台市',
    # 四国
    'takamatsu_marugame': '高松市',
    'kagawa_keisatsu': '高松市',
    'matsuyama_bantencho': '松山市',
    # 北陸
    'niigata_furumachi': '新潟市',
    'kanazawa_katamachi': '金沢市',
    # 静岡
    'hamamatsu_kasai_visit': '浜松市',
    'shizuoka_kenkei_drills': '静岡市',
    # 九州各県
    'saga_periphery_tokuryu': '佐賀市',
    'nagasaki_tokuryu': '長崎市',
    'kumamoto_tokuryu': '熊本市',
    'miyazaki_tokuryu': '宮崎市',
    'kagoshima_tokuryu': '鹿児島市',
    'oita_tokuryu': '大分市',
    'okayama_tokuryu': '岡山市',
    # 沖縄
    'okinawa_kyokuryukai_main': '那覇市',
    'koza_okinawa': '沖縄市',
    'compare_kyokuryukai_hq': '那覇市',
    'okinawa_tokuryu_serial': '那覇市',
    # 久留米
    'kurume_dojinkai_main_hq': '久留米市',
    'kurume_dojinkai_hq': '久留米市',
    'kurume_seidokai_hq': '久留米市',
    'kurume_namikawakai_hq': '久留米市',
    'kurume_bunkagai': '久留米市',
    'kurume_bunkagai_central': '久留米市',
    'kurume_keisatsu': '久留米市',
    'kurume_west_arcade': '久留米市',
    'kurume_jr_station': '久留米市',
    'kurume_shrine_temple': '久留米市',
    'compare_namikawakai_hq': '久留米市',
}


def kind_to_tier(kind: str) -> str:
    """tier (city / pref / national / intl) を kind から推定"""
    if kind in ('city_gov',): return 'city'
    if kind in ('pref_gov',): return 'pref'
    if kind in ('pref_police',): return 'pref'  # 県警を pref として
    return 'pref'  # default


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # Add tier column if missing
    cols = [r[1] for r in cur.execute('PRAGMA table_info(local_media)').fetchall()]
    if 'tier' not in cols:
        cur.execute('ALTER TABLE local_media ADD COLUMN tier TEXT DEFAULT "pref"')
        print('Added tier column to local_media')

    # Re-derive tier for existing entries based on kind
    cur.execute("UPDATE local_media SET tier='city'  WHERE kind='city_gov'")
    cur.execute("UPDATE local_media SET tier='pref'  WHERE kind IN ('pref_gov','newspaper','tv','radio','magazine','bouhai_center') AND tier IS NULL OR tier='pref'")
    cur.execute("UPDATE local_media SET tier='intl'  WHERE name LIKE '%大使館%' OR name LIKE '%日本国%大使館%'")

    sites = {row[1]: row[0] for row in cur.execute('SELECT id, slug FROM site')}

    # Now add city-detail entries
    inserted = 0; assigned = 0; missing_slug = []; missing_city = set()
    for slug, city_or_ward in SLUG_TO_CITYWARD_DETAIL.items():
        sid = sites.get(slug)
        if sid is None: missing_slug.append(slug); continue
        media = CITY_DETAIL.get(city_or_ward)
        if media is None: missing_city.add(city_or_ward); continue
        assigned += 1
        # Insert/upsert; use city tier
        for kind, name, url, note in media:
            # Determine tier: city_gov / city_police = city; else pref-like
            tier = 'city'
            if kind == 'pref_police' and ('警察署' in name or '警察' in name):
                tier = 'city'  # ward-level police is city-tier
            cur.execute('DELETE FROM local_media WHERE site_id=? AND name=?',
                        (sid, name))
            cur.execute(
                'INSERT INTO local_media(site_id, kind, name, url, note, ord, tier) '
                'VALUES (?,?,?,?,?,?,?)',
                (sid, kind, name, url, note, 5, tier))  # ord=5 to come first
            inserted += 1

    # Promote any existing city_gov entries to ord=5 so they show first
    cur.execute("UPDATE local_media SET ord=5 WHERE tier='city'")

    con.commit()
    total = cur.execute('SELECT COUNT(*) FROM local_media').fetchone()[0]
    by_tier = cur.execute(
        'SELECT tier, COUNT(*) FROM local_media GROUP BY tier'
    ).fetchall()
    print(f'phase48_city_media: +{inserted} city/ward entries across {assigned} sites')
    print(f'  total local_media: {total}')
    for t, c in by_tier: print(f'  {t}: {c}')
    if missing_slug:
        print(f'  WARN: {len(missing_slug)} unknown slugs: {missing_slug[:5]}')
    if missing_city:
        print(f'  WARN: {len(missing_city)} unknown cities: {sorted(missing_city)}')
    con.close()


if __name__ == '__main__':
    main()
