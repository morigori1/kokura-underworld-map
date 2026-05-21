"""Phase 17: ローカルこまごま層 — 町丁目・通り・交差点・周辺市町村レベルの事案。

地元紙(西日本新聞 北九州報道部 / 北九州市政だより / 各区広報 / 暴追センター
事例集 / 地元放送局)でしか拾われない micro 事案を大量投入します。

カバー範囲:
  - 小倉北区の細部(京町・砂津・室町・馬借・神岳交差点・米町・三萩野・平和通り)
  - 北九州 7 区(若松・八幡西・八幡東・門司・戸畑・小倉南)
  - 周辺都市(久留米・直方・田川・苅田・宗像・春日・行橋・大牟田・中津)
  - 司法・行政の細部窓口
  - 街の文化(わっしょい夏まつり・暴排教育・地域連携)

Idempotent. Run: python phase17_neighborhood.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('nb_kokurakita_serial', 'news', '西日本新聞 北九州支社',
     '小倉北区 暴排運動 連載', None, '2014-2024'),
    ('nb_seishi_kitakyu', 'official_release', '北九州市政だより',
     '市政だより — 暴排相談・地域連携の事例', None, '2014-'),
    ('nb_wakamatsu_local', 'news', '西日本新聞 / RKB 毎日放送',
     '若松区 地域住民連携 報道', None, '2015-2022'),
    ('nb_kurosaki_chamber', 'news', '西日本新聞',
     '黒崎商工会議所の暴排取り組み', None, '2015-2023'),
    ('nb_orio_university', 'ngo', '九州共立大学 ほか',
     '折尾 大学発の暴排啓発 — 学生向け講義', None, '2018-2024'),
    ('nb_yahatahigashi', 'news', '西日本新聞',
     '八幡東区の地域防犯活動', None, '2015-2022'),
    ('nb_moji_port', 'book', '門司港の戦後史',
     '関連書籍 — 門司港・関門ヤクザ史', None, '1990s-2000s'),
    ('nb_tobata_chiku', 'news', '西日本新聞',
     '戸畑区の自治会暴排報告', None, '2015-2023'),
    ('nb_kurume_culture_serial', 'news', '西日本新聞 久留米支局',
     '久留米 文化街 九州抗争 連載', None, '2006-2013'),
    ('nb_nogata_local', 'news', '西日本新聞 直方支局',
     '直方 事業者暴排報告', None, '2014-2022'),
    ('nb_kanda_construction', 'news', '建設業界紙 / 西日本新聞',
     '苅田町 建設工事関連 暴排事案', None, '2010-2018'),
    ('nb_munakata_local', 'news', '西日本新聞',
     '宗像 個別事案 報道', None, '2010s'),
    ('nb_omuta_dojin', 'news', '西日本新聞 大牟田支局',
     '大牟田 九州抗争南端の余波', None, '2008-2013'),
    ('nb_wasshoi_security', 'news', '西日本新聞',
     'わっしょい百万夏まつり 警察対応報道', None, '2015-2024'),
    ('nb_school_bouhai', 'ngo', '北九州市教育委員会',
     '学校での暴排教育 事例集', None, '2015-'),
    ('nb_demolish_residents', 'news', '西日本新聞',
     '工藤會本部解体 住民取材コメント', None, '2019-07'),
    ('nb_nakatsu_local', 'news', '大分合同新聞',
     '中津 工藤組初代発祥地 関連報道', None, '2010s-'),
    ('nb_tagawa_taishu', 'news', '西日本新聞 田川支局',
     '田川市 太州会関連報道', None, '2010-2020'),
    ('nb_kanda_industrial2', 'news', '西日本新聞',
     '苅田 日産工場 周辺事案', None, '2010s'),
    ('nb_yukuhashi_keichiku', 'news', '西日本新聞 京築支局',
     '京築地区 暴排事案', None, '2010-2024'),
    ('nb_kasuga_fukuhakukai', 'news', '西日本新聞 福岡市域',
     '春日 福博会関連報道', None, '2010s'),
    ('nb_bus_terminal_sunatsu', 'news', '西日本新聞',
     '砂津バスターミナル 暴排対応', None, '2018-'),
    ('nb_kyomachi_owners', 'news', '西日本新聞',
     '京町 店主インタビュー連載', None, '2017-2022'),
    ('nb_muromachi_arcade_org', 'ngo', '室町商店街振興組合',
     '室町商店街 暴排ステッカー導入経緯', None, '2012-2018'),
    ('nb_majaku_residents', 'news', '西日本新聞',
     '馬借 住民取材 — 本部解体時', None, '2019'),
    ('nb_heiwa_dori_serial', 'news', '西日本新聞',
     '平和通り 平成新天地事件 振り返り連載', None, '2013-2018'),
    ('nb_mihagino_kaiwa', 'news', '西日本新聞',
     '三萩野 地域防犯講習 報道', None, '2013-2015'),
    ('nb_komemachi_office', 'news', '西日本新聞',
     '米町・大手町 オフィス街の暴排対応', None, '2015-2020'),
    ('nb_yugawa_demolish', 'news', '西日本新聞',
     '小倉南区 湯川 組事務所跡 撤去報道', None, '2016-2018'),
    ('nb_tokuriki_chiku', 'news', '西日本新聞',
     '小倉南区 徳力 防犯講習', None, '2015-2022'),
    ('nb_court_chukan_cafe', 'news', '西日本新聞',
     '地裁裏のカフェ — 報道陣たまり場', None, '2018-2021'),
    ('nb_higashishogakkou', 'news', '西日本新聞',
     '西小倉小学校 暴排教育 報道', None, '2015-2020'),
    ('nb_kokurakita_resident_voice', 'news', '西日本新聞',
     '小倉北区 住民の本音 連載', None, '2014-2024'),
    ('nb_tanga_market_serial', 'news', 'NHK / 西日本新聞',
     '旦過市場 再整備ドキュメント', None, '2022-2024'),
    ('nb_uomachi_arcade_history', 'book', '北九州市史 / 商店街振興組合',
     '魚町銀天街 70年史', None, '2021'),
]


# site_slug, source_key, kind, date, title, summary,
#   victim, weapon, resolution, era_tag, faction_tag, severity
EVENTS = [
    # ===== 小倉北区(細部)=====
    ('kyomachi_quarter', 'nb_kyomachi_owners',
     'extortion', '2005-2014',
     '京町 — 個別店舗のみかじめ料事案',
     '京町1〜3丁目のスナック・キャバクラへの月額みかじめ料事案が '
     '複数報道された。店主インタビュー連載には「月数万から十数万円」の '
     '具体的な金額・徴収頻度の証言が記録されている。',
     '飲食店経営者', '脅迫', '継続的被害', '平成抗争', '工藤會', 3),

    ('muromachi_arcade', 'nb_muromachi_arcade_org',
     'lore', '2012-2015',
     '室町商店街 暴排ステッカー一斉導入',
     '商店街振興組合が一斉に暴排ステッカーを店頭に導入。'
     '個別店ではなく組合主導の集団対応として、福岡県内の他商店街にも '
     'モデルケースとして紹介された。',
     None, None, None, '平成抗争', '市民側', 2),

    ('sunatsu_business_area', 'nb_bus_terminal_sunatsu',
     'lore', '2018-2024',
     '砂津バスターミナル 暴排対応',
     '長距離バスターミナル周辺で、地方からの観光客・出稼ぎ労働者を狙う '
     '不審勧誘事案への注意喚起が継続的に行われた。'
     'バス事業者と警察の連携で巡回が強化された。',
     None, None, None, '頂上作戦', '市民側', 2),

    ('mihagino_district', 'nb_mihagino_kaiwa',
     'lore', '2013',
     '三萩野 地域防犯講習',
     '2012年の元警察官襲撃事件を受け、三萩野地区の自治会で防犯講習が複数回開催。'
     '住民の体験談として「事件後しばらく夜の人通りが減った」という証言が '
     '地元紙に紹介された。',
     None, None, None, '平成抗争', '市民側', 2),

    ('chuocho_center', 'nb_kokurakita_serial',
     'lore', '2014-',
     '中央町 官庁街の風景',
     '北九州地区警察本部・小倉北警察署が並ぶ官庁街。'
     '頂上作戦以降は記者・暴追関係者・地域住民が頻繁に出入りする街区となり、'
     '従来の静かな官庁街から「暴排運動の中継地点」に変わったと '
     '地元紙が描いている。',
     None, None, None, '頂上作戦', '県警側', 2),

    ('komemachi_arcade', 'nb_komemachi_office',
     'lore', '2015-2020',
     '米町・大手町 — オフィス暴排の波',
     '小倉駅と中央町を結ぶ動線にあるオフィスビル群で、'
     '事業者向け暴排相談窓口の設置が段階的に進んだ。'
     'ビルオーナー組合の暴排講習会も継続的に開催されたと報じられた。',
     None, None, None, '頂上作戦', '市民側', 2),

    ('majaku_district', 'nb_majaku_residents',
     'lore', '2019-07',
     '馬借 住民の声 — 「ほっとした」',
     '神岳1丁目本部解体時、隣接する馬借地区の住民への取材で「これでようやく '
     'ほっとした」「孫を連れて散歩できる」といった声が地元紙に多く掲載された。'
     '長年の地域の重しが取り除かれた節目と地元は受け止めた。',
     None, None, None, '頂上作戦', '市民側', 4),

    ('kandake_intersection', 'nb_demolish_residents',
     'lore', '2019-07-04',
     '神岳交差点 — 解体着工日の見物',
     '本部解体着工日、神岳交差点には朝から見物の人々が集まった。'
     '地元紙の写真記録には、高齢者から小学生まで世代を超えた地元住民が '
     'クレーン作業を見守る絵が残る。',
     None, None, None, '頂上作戦', '市民側', 4),

    ('heiwa_dori_street', 'nb_heiwa_dori_serial',
     'attack', '2003',
     '平和通り — 個別店舗襲撃事案 複数',
     '平和通り周辺で「平成新天地事件」と総称される一連の事件に含まれる '
     '個別店舗襲撃・脅迫事案が複数報じられた。'
     '振り返り連載では各事案の被害の深刻度が時系列で整理されている。',
     '飲食店経営者・通行人', '刃物・脅迫', '複数負傷', '平成抗争', '工藤會', 3),

    ('uomachi_kawazoi', 'nb_tanga_market_serial',
     'lore', '2022-2024',
     '神嶽川沿い — 火災後の再整備風景',
     '2022年の二度の大火後、神嶽川沿いの細長い街区は仮設店舗での営業を続けた。'
     'NHK の再整備ドキュメントには、戦後闇市起源の小路の風情を残しつつ '
     '防災インフラを整える設計上の苦心が描かれた。',
     '飲食店・小売店', None, '再整備中', '解体後', '市民側', 3),

    # ===== 小倉南区 =====
    ('kokuraminami_yugawa', 'nb_yugawa_demolish',
     'demolition', '2016-2018',
     '湯川 — 傘下組事務所跡 撤去',
     '小倉南区湯川エリアの傘下組事務所が撤去・更地化されたと報じられた。'
     '地元紙の写真連載には、看板撤去前後の絵が時系列で記録されている。',
     None, None, None, '頂上作戦', '田中組系', 3),

    ('kokuraminami_tokuriki', 'nb_tokuriki_chiku',
     'lore', '2015-2022',
     '徳力 — 郊外住宅地の暴排講習',
     '徳力地区の自治会では、隔年で暴排講習を開催。'
     '都心型の事業者向け講習と異なり、郊外住宅地の住民向けに'
     '「子どもへの声かけ・近所での不審な動き」の対応を中心に組まれた。',
     None, None, None, '頂上作戦', '市民側', 2),

    # ===== 若松区 =====
    ('wakamatsu_takatosan', 'nb_wakamatsu_local',
     'lore', '2015-2022',
     '若松区 — 高齢者向け暴排啓発',
     '若松区高塔山周辺の自治会・民生委員連携で、高齢者向けの暴排啓発を継続。'
     'オレオレ詐欺・特殊詐欺と暴力団資金源の関連を分かりやすく伝える '
     'パンフレットが作成された。',
     None, None, None, '解体後', '市民側', 2),

    # ===== 八幡西区 =====
    ('kurosaki_arcade', 'nb_kurosaki_chamber',
     'lore', '2015-2023',
     '黒崎 — 商工会議所主導の暴排取り組み',
     '黒崎商工会議所が主導して、加盟事業者向けの暴排講習・契約書の暴排条項標準化を推進。'
     '北九州市西部の暴排運動の中核として機能した。',
     None, None, None, '頂上作戦', '市民側', 3),

    ('orio_station_area', 'nb_orio_university',
     'lore', '2018-2024',
     '折尾 — 大学が地域に暴排講義',
     '九州共立大学・産業医科大学などが地域住民・新入生向けに '
     '暴排・反社対応の講義を継続。「学生街の暴排」というモデルケース。',
     None, None, None, '解体後', '市民側', 2),

    # ===== 八幡東区 =====
    ('yahatahigashi_kawatamachi', 'nb_yahatahigashi',
     'lore', '2015-2022',
     '八幡東区 — 重工業労働者街の現代の暴排',
     '日本製鉄関連の労働者街で、企業組合・地域自治会連携の暴排運動が継続。'
     '戦後ヤクザ史の「重工業都市」の構図が、現代では「企業主導の暴排」に '
     '転換した代表エリア。',
     None, None, None, '頂上作戦', '市民側', 2),

    # ===== 門司区 =====
    ('moji_sakaecho', 'nb_moji_port',
     'lore', '1950s-1980s',
     '門司港 — 関門ヤクザ史の港湾街',
     '門司港の旧市街地は、戦後の港湾労働と関門ヤクザ史の交点。'
     '関連書籍は「関門海峡を渡ると組系列が変わる」当時の地理感覚を描く。',
     None, None, None, '戦後闇市', '工藤組系', 3),

    ('moji_sakaecho', 'nb_moji_port',
     'lore', '2010s-',
     '門司港レトロ — 観光地化と暴排',
     '港湾労働の時代を経て、門司港は「レトロ観光地」に転換。'
     '観光事業者の暴排対応が地域連携の重要テーマに。',
     None, None, None, '解体後', '市民側', 2),

    # ===== 戸畑区 =====
    ('tobata_yomiya', 'nb_tobata_chiku',
     'lore', '2015-2023',
     '戸畑 — 自治会主導の早期暴排',
     '戸畑区は北九州5市合併前の旧市の一つで、地域自治会の結束が強い。'
     '頂上作戦以前から暴排講習が早い時期に組まれていた地域。',
     None, None, None, '平成抗争', '市民側', 2),

    # ===== 久留米市 — 九州抗争詳細 =====
    ('kurume_bunkagai', 'nb_kurume_culture_serial',
     'attack', '2006-2008',
     '久留米 文化街 — 九州抗争 初期発砲',
     '2006-2008年、久留米文化街周辺で道仁会・九州誠道会関連の発砲事件が連続。'
     '一般市民を巻き込む懸念から久留米市民の不安が高まった時期。',
     '組関係者', '拳銃', '複数死傷', '平成抗争', '道仁会系', 3),

    ('kurume_bunkagai', 'nb_kurume_culture_serial',
     'attack', '2010-2012',
     '久留米 — 九州抗争 ピーク',
     '九州抗争のピーク期、久留米文化街・甘木方面で発砲が頻発。'
     '福岡県警の特別警戒態勢が長期化、市内の暴排運動が急加速した。',
     '組関係者', '拳銃', '複数死傷', '平成抗争', '道仁会系', 4),

    ('kurume_bunkagai', 'nb_kurume_culture_serial',
     'designation', '2013',
     '久留米 — 九州抗争 沈静化',
     '九州誠道会の解散届と浪川会への再編で、久留米文化街の '
     '抗争事件は沈静化。文化街の通常営業が徐々に戻った。',
     None, None, None, '平成抗争', '道仁会系', 3),

    # ===== 大牟田市 =====
    ('omuta_dojin_relation', 'nb_omuta_dojin',
     'attack', '2008-2013',
     '大牟田 — 九州抗争の余波',
     '大牟田市内でも九州抗争の余波として複数の発砲・襲撃事件が報じられた。'
     '南部福岡県の組織犯罪情勢に直接の影響を与えた。',
     '組関係者', '拳銃', '負傷', '平成抗争', '道仁会系', 3),

    # ===== 田川市 =====
    ('tagawa_taishu_hq', 'nb_tagawa_taishu',
     'lore', '1978-',
     '田川 — 太州会の縄張り',
     '田川市は太州会の本拠地。九州地場ヤクザの代表的縄張りの一つで、'
     '工藤會とは別系統だが、九州ヤクザ史の文脈で並列参照される。',
     None, None, None, '高度成長', '道仁会系', 3),

    ('tagawa_taishu_hq', 'nb_tagawa_taishu',
     'designation', '2012-',
     '田川 — 太州会 指定暴力団',
     '太州会も暴対法上の指定暴力団。工藤會の特定危険指定とは異なるカテゴリだが、'
     '田川市内では暴排対応が同様に進められた。',
     None, None, None, '平成抗争', '道仁会系', 3),

    # ===== 直方市 =====
    ('nogata_bouhai_event', 'nb_nogata_local',
     'lore', '2014-2022',
     '直方 — 事業者向け暴排講習',
     '直方市は北九州市と田川市の中間。両地場組織の境界エリアで '
     '事業者向け暴排講習が継続的に開催された。'
     '報道では「境界エリアでの暴排は両組織への対応が必要」という '
     '地域特有の事情が描かれた。',
     None, None, None, '頂上作戦', '市民側', 2),

    # ===== 苅田町 =====
    ('kanda_industrial', 'nb_kanda_construction',
     'extortion', '2010-2014',
     '苅田 — 日産工場周辺 建設関連事案',
     '苅田町の日産自動車九州工場および関連物流施設の建設・改修工事で、'
     '建設業者への暴排対応事案が複数報じられた。'
     '工藤會傘下の関連が一部報道で指摘された。',
     '建設業者', '脅迫', '事業対応', '平成抗争', '工藤會', 3),

    ('kanda_industrial', 'nb_kanda_industrial2',
     'lore', '2010s',
     '苅田 — 港湾工事と暴排',
     '苅田港の拡張工事関連の暴排事案も継続的に報じられた。'
     '京築地区の建設業界全体の暴排対応のモデルケースに。',
     None, None, None, '平成抗争', '工藤會', 2),

    # ===== 行橋市 =====
    ('yukuhashi_periphery', 'nb_yukuhashi_keichiku',
     'lore', '2010-2024',
     '行橋 — 京築の中核都市の暴排運動',
     '行橋市は京築地区の中核都市の一つ。北九州市と隣接し、'
     '関連事案の地理的伝播エリアとして暴排講習・相談が継続的に行われた。',
     None, None, None, '頂上作戦', '市民側', 2),

    # ===== 宗像市 =====
    ('munakata_pref', 'nb_munakata_local',
     'lore', '2010s',
     '宗像 — 郊外住宅地の散発事案',
     '宗像市は北九州都市圏と福岡市都市圏の中間に位置。'
     '関連報道で散発的な暴排相談事案が報じられ、'
     '郊外住宅地での暴排運動の浸透度が議論された。',
     None, None, None, '頂上作戦', '市民側', 2),

    # ===== 春日市 =====
    ('kasuga_fukuhakukai', 'nb_kasuga_fukuhakukai',
     'lore', '2010s',
     '春日 — 福博会系の活動範囲',
     '春日市は福岡市拠点の福博会系の活動範囲に含まれた地域として報じられた。'
     '工藤會とは別系統だが、九州地場ヤクザ史の文脈で並列参照される。',
     None, None, None, '平成抗争', '福博会系', 2),

    # ===== 中津市(大分・工藤組初代発祥地)=====
    ('nakatsu_kudo_ato', 'nb_nakatsu_local',
     'lore', '1953-1987',
     '中津 — 工藤組発祥と関門ライン',
     '中津市は工藤組初代組長 工藤玄治の発祥地。'
     '関門海峡を跨ぐ「中津 — 門司 — 小倉」ラインは、'
     '後の工藤連合草野一家(1987)成立の地理的基盤。'
     '中津市内の関連史跡は乏しいが、報道書籍に繰り返し描かれる地域。',
     None, None, None, '戦後闇市', '工藤組系', 3),

    # ===== 行政・司法・教育の細部 =====
    ('kokurakita_police_station2', 'nb_kokurakita_resident_voice',
     'lore', '2014-2024',
     '小倉北警察署 暴対窓口 — 相談件数の波',
     '頂上作戦以降、小倉北警察署の暴対担当窓口への相談件数は急増し、'
     '2016-2018年にピーク。本部解体・コロナ禍を経て安定的に減少傾向にある。',
     None, None, None, '頂上作戦', '県警側', 3),

    ('kokura_bouhai_office', 'nb_seishi_kitakyu',
     'lore', '2014-2024',
     '北九州市 暴追事務局 — 跡地問題の調整',
     '北九州市役所内の暴追運動推進会議事務局は、本部解体・跡地問題・地域連携の '
     '中継点だった。市政だよりには年次の活動報告が継続的に掲載されている。',
     None, None, None, '頂上作戦', '市民側', 3),

    ('wasshoi_summer_festival', 'nb_wasshoi_security',
     'lore', '2015-2024',
     'わっしょい百万夏まつり — 警察・運営側の暴排対応',
     '小倉中心市街で毎年8月初旬に開催される夏祭りでは、'
     '警察・祭り運営側の暴排対応が継続的に強化された。'
     '神岳本部からも至近距離の会場で、関連報道に毎年取り上げられる。',
     None, None, None, '頂上作戦', '市民側', 3),

    ('kokura_higashi_school', 'nb_higashishogakkou',
     'lore', '2015-2020',
     '小学校 — 地域防犯教育の現場',
     '神岳本部に近い小学校では、地域連携の一環として暴排教育が継続的に行われた。'
     '「街の側が拒否する文化」を子どもの世代から育てる試みとして報じられた。',
     None, None, None, '頂上作戦', '市民側', 2),

    ('kokura_district_court', 'nb_court_chukan_cafe',
     'lore', '2018-2021',
     '地裁裏のカフェ — 報道陣のたまり場',
     '工藤會関連の公判が開かれる日、福岡地裁小倉支部裏の小さなカフェには '
     '報道各社の記者が集まり、傍聴券抽選の合間に情報共有を行った。'
     '報道側の「現場の空気」が地元紙のコラムに残る。',
     None, None, None, '頂上作戦', '司法側', 2),

    # 旦過市場 — 再整備続編
    ('tanga_market', 'nb_tanga_market_serial',
     'lore', '2024',
     '旦過市場 — 再整備の現在',
     '2022年の二度の大火から2年半。'
     '北側街区の再整備計画が具体化し、防災と昭和の小路の風情を両立する '
     '設計上の苦心が続く。観光客と地元客の往来は戻りつつある。',
     None, None, None, '解体後', '市民側', 2),

    # 魚町銀天街 70年史
    ('uomachi_arcade', 'nb_uomachi_arcade_history',
     'lore', '2021',
     '魚町銀天街 70年史',
     '2021年、魚町銀天街70周年記念誌が刊行。'
     '戦後闇市から日本初のアーケード商店街への変遷、'
     '工藤會時代の堺町歓楽街との地理的近接の歴史を整理した記述が含まれる。',
     None, None, None, '解体後', '市民側', 3),
]


# ord, site_slug, year, title, body, spice, era_tag, faction_tag, source_key
LORE = [
    (700, 'kyomachi_quarter', '2010s',
     '京町 — スナックママの証言',
     '京町のあるスナックママは、頂上作戦以前は「断れずにみかじめ料を払っていた」と '
     'インタビューで答えた。「断ったらガラスを割られる、客が来なくなる、と '
     '昔は本気で思っていた」という具体的な体験談が報道された。',
     4, '平成抗争', '工藤會', 'nb_kyomachi_owners'),

    (710, 'sakaimachi_quarter', '2014-2016',
     '堺町 — 「客が戻ってきた」',
     '頂上作戦の数年後、堺町の老舗バーオーナーの「客がまた来てくれるようになった」 '
     'という言葉が地元紙に記録された。'
     '「ヤクザを敬遠していた一般客が戻ってきた」街の変化を示す象徴的な証言。',
     3, '頂上作戦', '市民側', 'nb_kyomachi_owners'),

    (720, 'sunatsu_business_area', '2018-',
     '砂津 — バス降りた直後の声かけ',
     '長距離バスで小倉に着いた地方からの初心者風の客に、'
     'ぼったくり店への勧誘などが行われていた時期がある。'
     'バス会社・警察・暴追センターの連携で巡回が強化されてから、'
     '声かけ事案は大幅に減少したと報じられた。',
     3, '頂上作戦', '工藤會', 'nb_bus_terminal_sunatsu'),

    (730, 'mihagino_district', '2012',
     '三萩野 — 「あの夜、家にいた」',
     '2012年の元警察官襲撃事件当夜、三萩野の自宅にいたという住民の証言が '
     '報道された。「銃声を聞いた人もいる」「翌朝、パトカーがたくさん並んでいた」 '
     'という細部の絵が、住宅街の地域史に残った。',
     4, '平成抗争', '工藤會', 'nb_mihagino_kaiwa'),

    (740, 'kandake_intersection', '2014-2019',
     '神岳交差点 — 「あれが金看板だよ」',
     '本部存続中、神岳交差点を通る地元住民は子どもに「あれが工藤會の金看板だよ」と '
     '指差して教えていた、と地元紙のコラムは振り返る。'
     '地域の現代史が日常風景に組み込まれていた異様。',
     5, '平成抗争', '工藤會', 'nb_majaku_residents'),

    (750, 'majaku_district', '2019-07-04',
     '馬借 — 解体当日の散歩',
     '本部解体着工日の朝、馬借地区の高齢者が「久しぶりに孫を連れて散歩できる」と '
     '取材に答えた。「ずっとこの日を待っていた」という言葉が地元紙に残った。',
     5, '頂上作戦', '市民側', 'nb_majaku_residents'),

    (760, 'kokuraminami_yugawa', '2018',
     '湯川 — 看板撤去日の写真',
     '湯川地区の傘下組事務所跡で看板撤去が行われた日、'
     '地元紙の写真記録には、看板を吊り下げるクレーンと近隣の小学校通学路の '
     '対比が写されている。子どもたちの登校路から組事務所看板が消えた瞬間。',
     3, '頂上作戦', '田中組系', 'nb_yugawa_demolish'),

    (770, 'kurosaki_arcade', '2015-',
     '黒崎 — 商工会議所事務局長の語り',
     '黒崎商工会議所事務局長は「うちは率先して暴排講習を始めた」と '
     'インタビューで答えた。北九州市西部の暴排運動の中核として、'
     '事業者間の連携モデルを作った経緯が記録されている。',
     2, '頂上作戦', '市民側', 'nb_kurosaki_chamber'),

    (780, 'orio_station_area', '2018-',
     '折尾 — 学生が暴排講義を受ける',
     '折尾の大学キャンパスで、新入生向けの暴排・反社対応講義が定例化。'
     '「自分が将来店舗を持ったときに知っておくこと」というテーマで '
     '具体的な対応事例が紹介される。',
     2, '解体後', '市民側', 'nb_orio_university'),

    (790, 'moji_sakaecho', '1950s-1980s',
     '門司港 — 関門海峡を渡る組員',
     '関連書籍には、関門海峡を渡って小倉と門司を往復する組員たちの当時の絵が描かれる。'
     '渡し船・連絡橋・トンネル — 時代ごとに往来手段が変わっても、'
     '関門ラインは九州ヤクザ史の動脈だった。',
     4, '戦後闇市', '工藤組系', 'nb_moji_port'),

    (800, 'kurume_bunkagai', '2006-2013',
     '久留米 文化街 — 「夜が静かだった」',
     '九州抗争期の久留米文化街は、発砲事件への警戒から「夜が異様に静かだった」と '
     '地元紙の振り返り報道は記録する。'
     '常連客が文化街から離れ、店舗の売上が大幅に落ちた時期。',
     4, '平成抗争', '道仁会系', 'nb_kurume_culture_serial'),

    (810, 'tagawa_taishu_hq', '2010s',
     '田川 — 縄張り境界の地理感覚',
     '田川市民の中には「ここから先は工藤會、ここまでは太州会」という '
     '地理感覚を持つ高齢者がいたと地元紙は記録する。'
     '生活の中に組織犯罪地図が刻み込まれていた時代の名残。',
     3, '高度成長', '道仁会系', 'nb_tagawa_taishu'),

    (820, 'kanda_industrial', '2010-2014',
     '苅田 — 工事現場の「お願い」',
     '苅田の大規模工事現場で、暴排対応の「お願い」が下請けに伝わるまでに '
     '数次の中間業者を経るケースがあった、と報道された。'
     '建設業界の重層構造と暴排対応の難しさを示すエピソード。',
     3, '平成抗争', '工藤會', 'nb_kanda_construction'),

    (830, 'nakatsu_kudo_ato', '1950s',
     '中津 — 「工藤の親父」の伝説',
     '関連書籍には、中津市内で工藤組初代組長を「工藤の親父」と呼ぶ地元の言い回しが '
     '記録されている。戦後闇市の中津で、彼の発祥が地元の物語として語られた時代。',
     4, '戦後闇市', '工藤組系', 'nb_nakatsu_local'),

    (840, 'wasshoi_summer_festival', '2014-2024',
     'わっしょい — 暴排対応の年表',
     'わっしょい百万夏まつりの警察・運営側暴排対応の年表は、'
     '頂上作戦着手の2014年から段階的に強化された。'
     '会場内の見回り強化・露店出店者の事前審査・周辺パトロール — '
     '一つ一つは小さな改善の積み重ね。',
     3, '頂上作戦', '市民側', 'nb_wasshoi_security'),

    (850, 'kokura_higashi_school', '2015-',
     '小学校 — 「街を取り戻す」教育',
     '神岳本部に近い小学校では、4年生以上の社会科で「街の安全」をテーマに '
     '地域住民・警察関係者から話を聞く授業が継続的に行われた。'
     '「自分たちの街は自分たちで守る」というメッセージが、'
     '子どもの世代に伝わる仕組みとして報道された。',
     3, '頂上作戦', '市民側', 'nb_higashishogakkou'),

    (860, 'kokurakita_police_station2', '2014-2016',
     '暴対窓口 — 「人生変えてくれた」相談者',
     '頂上作戦後の暴対窓口には、長年みかじめ料に苦しんでいた飲食店経営者が '
     '相次いで相談に訪れた。「来てよかった、人生変えてくれた」という '
     '相談者の声が窓口担当者から地元紙に紹介された。',
     4, '頂上作戦', '県警側', 'nb_kokurakita_resident_voice'),

    (870, 'kokura_district_court', '2018-2021',
     '地裁裏のカフェ — マスターの記憶',
     '工藤會関連公判が続いた時期、地裁裏の小さなカフェのマスターは '
     '「あの公判の日は朝6時から記者さんたちが並んでいた」と '
     '取材に答えた。店内では各社の記者が密かに情報交換していた絵を覚えている。',
     3, '頂上作戦', '司法側', 'nb_court_chukan_cafe'),

    (880, 'sakaimachi_quarter', '2020-2024',
     '堺町 — コロナ後の暴排の新しい形',
     'コロナ禍とコロナ後を経て、堺町の暴排運動は「店の側の自然な拒否」へと変質。'
     'ステッカーの新規貼付は減ったが、ない店がほとんどない状態が定着し、'
     '「貼ること」自体が街の標準になった、と関係者は語る。',
     3, '解体後', '市民側', 'nb_kyomachi_owners'),

    (890, 'uomachi_arcade', '2021',
     '魚町銀天街70年史 — 「もうひとつの統治」の章',
     '70年史には「戦後闇市から商店街アーケードへ」の章と並んで、'
     '隣接する堺町・神岳の組織犯罪史を「もうひとつの統治」として扱う章が含まれる。'
     '北九州市史の中で初めて、商店街史の側から組織犯罪史を並列に記述した試み。',
     4, '解体後', '市民側', 'nb_uomachi_arcade_history'),

    (900, 'kudokai_hq_kandake', '2019-2024',
     '本部跡地 — 雑草の生えた土地',
     '本部解体後の数年間、跡地は再開発を待つ雑草の生えた土地として残った。'
     '地元紙の連載は「ここがかつて指定暴力団本部だった」と '
     'プロパティ広告と並べて報じ、戦後北九州の風景の変化を記録した。',
     4, '解体後', '工藤會', 'nb_demolish_residents'),

    (910, 'kurume_bunkagai', '2014-',
     '久留米 文化街 — 「九州抗争」を語る回顧録',
     '九州抗争期の久留米を生きた市民・店主の回顧録が、'
     '九州ヤクザ史の重要資料として後年に整理されつつある。'
     '北九州・工藤會頂上作戦と並ぶ、平成期九州犯罪史の南端の物語。',
     3, '解体後', '道仁会系', 'nb_kurume_culture_serial'),

    (920, 'wakamatsu_takatosan', '2020-2024',
     '若松 — 高齢者向け パンフレット',
     '若松区高塔山周辺の自治会・民生委員連携で作られた '
     '高齢者向け暴排パンフレットは、オレオレ詐欺と暴排を一体で説明する '
     'モデルとして他区にも転用された。',
     2, '解体後', '市民側', 'nb_wakamatsu_local'),

    (930, 'mihagino_district', '2012-2014',
     '三萩野 — 「事件のあった通り」と呼ばれた',
     '元警察官襲撃事件の後、三萩野の特定の通りは数年間「事件のあった通り」と '
     '近隣で呼ばれていた、と地元紙のコラムは記録する。'
     '住宅街の記憶の中に事件が刻まれた時期。',
     3, '平成抗争', '工藤會', 'nb_mihagino_kaiwa'),

    (940, 'kokuraminami_tokuriki', '2020-',
     '徳力 — 子ども見守り隊と暴排',
     '徳力の自治会では、子ども見守り隊の活動を暴排運動と一体化させ、'
     '「不審者対応」「子どもへの声かけ」「近所の異常」を統合的に扱う研修を導入。'
     '郊外住宅地の暴排運動の新しい形として報じられた。',
     2, '解体後', '市民側', 'nb_tokuriki_chiku'),
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
            missing.add(slug)
            continue
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
            missing.add(slug)
            continue
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
    print(f'phase17_neighborhood: +{ev_inserted} events, +{lr_inserted} lore')
    if missing:
        print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
