"""Phase 24: 半グレ・トクリュウの個別事例さらに深掘り + 他地域(沖縄・京都・名古屋・大阪)。

Idempotent. Run: python phase24_more_cases.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('mc_inagi_2022', 'news', '朝日新聞 / 警視庁',
     '稲城市 高齢者強盗(2022 前兆事案)報道', None, '2022'),
    ('mc_chiba_isumi', 'news', '朝日新聞 / 千葉日報',
     '千葉県内連続強盗報道(2023)', None, '2023'),
    ('mc_saitama_warabi', 'news', '朝日新聞 / 埼玉新聞',
     '埼玉県蕨市 強盗報道(2023)', None, '2023'),
    ('mc_ibaraki_chikusei', 'news', '茨城新聞 / 朝日新聞',
     '茨城県筑西市 強盗報道(2023)', None, '2023'),
    ('mc_tochigi_oyama', 'news', '下野新聞 / 朝日新聞',
     '栃木県小山市 強盗報道(2023)', None, '2023'),
    ('mc_kanagawa_robbery', 'news', '神奈川新聞 / 朝日新聞',
     '神奈川県内 連続強盗報道(2023-2024)', None, '2023-2024'),
    ('mc_osaka_tokuryu', 'news', '産経新聞 / 朝日新聞',
     '大阪府内 トクリュウ強盗報道(2023-2024)', None, '2023-2024'),
    ('mc_aichi_nagoya', 'news', '中日新聞 / 朝日新聞',
     '愛知県名古屋市 強盗報道(2023-2024)', None, '2023-2024'),
    ('mc_hyogo_robbery', 'news', '神戸新聞 / 朝日新聞',
     '兵庫県神戸市 強盗報道(2024)', None, '2024'),
    ('mc_fukuoka_robbery', 'news', '西日本新聞 / 朝日新聞',
     '福岡県内 トクリュウ強盗報道(2024)', None, '2024'),
    ('mc_takasaki_gunma', 'news', '上毛新聞 / 朝日新聞',
     '群馬県高崎市 強盗報道(2023)', None, '2023'),
    ('mc_niigata_robbery', 'news', '新潟日報',
     '新潟県 トクリュウ強盗報道(2024)', None, '2024'),
    ('mc_sns_recruiter', 'news', '日経新聞 / 朝日新聞',
     'SNS リクルーター 摘発報道(2024-)', None, '2024-'),
    ('mc_atm_uketakedashi', 'news', '朝日新聞 / 警察庁',
     '出し子・受け子 連続摘発報道', None, '2020-'),
    ('mc_roman_sagi_book', 'book', '報道書籍 / 警察庁',
     'ロマンス詐欺 SNS 経由組織化', None, '2018-'),
    ('mc_kanto_rengo_ob', 'book', '報道書籍 / 工藤明男',
     '関東連合 OB の動向(解散後)', None, '2014-'),
    ('mc_ex_yakuza_tokuryu', 'book', '溝口敦 / 鈴木智彦',
     '元組員の現代型組織犯罪への流入', None, '2020-'),
    ('mc_okinawa_kyokuryu', 'book', '沖縄タイムス / 琉球新報',
     '旭琉会 戦後沖縄ヤクザ史', None, '1949-'),
    ('mc_koza_okinawa_book', 'book', '報道書籍',
     'コザ(沖縄市)の戦後ヤクザ文化', None, '1950s-'),
    ('mc_us_military_yakuza', 'book', '報道書籍',
     '沖縄米軍基地周辺のヤクザ史', None, '1950s-'),
    ('mc_aizukotetsu_book', 'book', '報道書籍 / 京都新聞',
     '会津小鉄会 京都ヤクザ史', None, '1869-'),
    ('mc_kyoto_gion_culture', 'book', '京都市史 / 報道書籍',
     '祇園 花街文化と組織犯罪', None, '1700s-'),
    ('mc_kodokai_book', 'book', '溝口敦 / 山平重樹',
     '弘道会(名古屋・山口組最大2次団体)', None, '1984-'),
    ('mc_nagoya_sakae', 'book', '中日新聞 / 中部経済新聞',
     '名古屋 栄 歓楽街と組織犯罪', None, '1990s-'),
    ('mc_osaka_minami_book', 'book', '報道書籍',
     '大阪ミナミ 関西地場ヤクザ', None, '1950s-'),
    ('mc_kamagasaki_book', 'book', '報道書籍',
     '釜ヶ崎(あいりん地区)戦後労働者街史', None, '1960s-'),
]


EVENTS = [
    # ===== トクリュウ 個別広域強盗 =====
    ('inagi_robbery_2022', 'mc_inagi_2022',
     'attack', '2022',
     '稲城市 高齢者強盗 — 2023連続強盗の前兆',
     '東京都稲城市で発生した高齢者宅強盗事件。'
     '後に2023年の連続強盗事件と同一指示役グループの関与が捜査で示唆された。'
     'トクリュウ型犯罪の組成期の事案として位置づけられる。',
     '高齢者', '鈍器', '重傷', '解体後', 'トクリュウ', 4),

    ('chiba_isumi_robbery', 'mc_chiba_isumi',
     'attack', '2023',
     '千葉県内 連続強盗(2023)',
     '千葉県内の複数地域で2023年に発生したトクリュウ型強盗事件。'
     '高齢者宅を狙った典型的な闇バイト型犯行。'
     '実行役は全て SNS 経由の即席募集だった。',
     '高齢者', '鈍器・刃物', '死傷', '解体後', 'トクリュウ', 4),

    ('saitama_warabi_robbery', 'mc_saitama_warabi',
     'attack', '2023-04',
     '埼玉県蕨市 強盗事件',
     '埼玉県蕨市の高齢者宅強盗事件。'
     '関東広域連続強盗の一部として捜査され、'
     '指示役の所在不明から数か月間捜査が継続した。',
     '高齢者', '鈍器', '負傷', '解体後', 'トクリュウ', 4),

    ('ibaraki_chikusei_robbery', 'mc_ibaraki_chikusei',
     'attack', '2023-10',
     '茨城県筑西市 強盗事件',
     '茨城県筑西市の高齢者宅強盗事件。'
     '北関東への拡散事例として2023年後半に報じられた。',
     '高齢者', '鈍器', '重傷', '解体後', 'トクリュウ', 4),

    ('tochigi_oyama_robbery', 'mc_tochigi_oyama',
     'attack', '2023-10',
     '栃木県小山市 強盗事件',
     '栃木県小山市の高齢者宅強盗事件。'
     '北関東広域への拡散の代表事例。',
     '高齢者', '鈍器・刃物', '死亡', '解体後', 'トクリュウ', 5),

    ('kanagawa_yokohama_robbery', 'mc_kanagawa_robbery',
     'attack', '2023-2024',
     '神奈川県 横浜市 連続強盗',
     '横浜市内で発生した複数の強盗事件。'
     '都市部の高齢者宅・宝石店を狙うトクリュウ型犯行。'
     '関東広域連続強盗の主要発生地の一つ。',
     '高齢者・店主', '鈍器・刃物', '死傷', '解体後', 'トクリュウ', 4),

    ('takasaki_gunma_robbery', 'mc_takasaki_gunma',
     'attack', '2023',
     '群馬県高崎市 強盗事件',
     '群馬県高崎市内の高齢者宅強盗事件。'
     '北関東広域強盗の一翼。',
     '高齢者', '鈍器', '重傷', '解体後', 'トクリュウ', 3),

    ('osaka_robbery_tokuryu', 'mc_osaka_tokuryu',
     'attack', '2023-2024',
     '大阪府内 トクリュウ強盗',
     '関東中心だった連続強盗が関西にも拡散。'
     '大阪府内で複数の強盗事件が報じられた。'
     '関西は伝統的に山口組地場で、新型組織犯罪との重複が議論された。',
     '高齢者・店主', '鈍器・刃物', '死傷', '解体後', 'トクリュウ', 4),

    ('aichi_nagoya_robbery', 'mc_aichi_nagoya',
     'attack', '2023-2024',
     '愛知県名古屋市 強盗',
     '名古屋市内のトクリュウ型強盗事件。'
     '中部圏への広域拡散の代表事例で、'
     '弘道会など伝統的山口組系の縄張りとは別系統で発生した。',
     '高齢者', '鈍器', '死傷', '解体後', 'トクリュウ', 4),

    ('hyogo_robbery_2024', 'mc_hyogo_robbery',
     'attack', '2024',
     '兵庫県神戸市 強盗',
     '兵庫県神戸市内で2024年に発生した強盗事件。'
     '六代目山口組総本部のある神戸でもトクリュウ型犯行が見られたことが '
     '組織犯罪情勢の象徴的事例として注目された。',
     '高齢者', '鈍器', '重傷', '解体後', 'トクリュウ', 4),

    ('fukuoka_robbery_2024', 'mc_fukuoka_robbery',
     'attack', '2024',
     '福岡県内 トクリュウ強盗',
     '福岡県内で2024年に報じられたトクリュウ型強盗事件。'
     '工藤會解体後の九州にも現代型組織犯罪が及んだ事例。',
     '高齢者', '鈍器', '重傷', '解体後', 'トクリュウ', 4),

    ('niigata_robbery_2024', 'mc_niigata_robbery',
     'attack', '2024',
     '新潟県内 強盗事件(2024)',
     '新潟県内のトクリュウ型強盗事件。'
     '日本海側への拡散の一例。'
     '太平洋側中心だった犯行が全国化していることを示す。',
     '高齢者', '鈍器', '負傷', '解体後', 'トクリュウ', 3),

    # ===== SNS リクルーター・出し子受け子 =====
    ('tokyo_sns_recruiter_office', 'mc_sns_recruiter',
     'arrest', '2024',
     'SNS リクルーター 摘発(東京)',
     '2024年、警視庁が東京都内の SNS 闇バイト募集側拠点を複数摘発。'
     '指示役側ではなく募集役側を摘発する新方針として注目された。',
     None, None, None, '解体後', 'トクリュウ', 4),

    ('osaka_sns_recruiter', 'mc_sns_recruiter',
     'arrest', '2024',
     'SNS リクルーター 摘発(大阪)',
     '関西でも闇バイト募集側の摘発が継続。'
     '指示役と募集役の分業構造が捜査で明らかになった。',
     None, None, None, '解体後', 'トクリュウ', 3),

    ('ulu_atm_demand', 'mc_atm_uketakedashi',
     'arrest', '2020-2024',
     '出し子・受け子 連続摘発',
     '特殊詐欺・トクリュウ事件で ATM での現金引き出し役・受け取り役の摘発が連続。'
     '実行役の若年層への広がりが社会問題化し、'
     '学校・自治体での予防啓発が強化された。',
     '若年層実行役', None, '逮捕', '解体後', 'トクリュウ', 3),

    ('roman_sagi_online', 'mc_roman_sagi_book',
     'lore', '2018-',
     'ロマンス詐欺 — マッチングアプリ経由の組織化',
     'マッチングアプリ・SNS 経由のロマンス詐欺が2018年以降組織化。'
     'トクリュウ型の海外拠点+国内実行役の構図が広がり、'
     '被害額は年間100億円規模に達した報告も。',
     '出会い系利用者', '詐欺', '金銭被害', '解体後', 'トクリュウ', 4),

    # ===== 関東連合 OB / 元組員流入 =====
    ('kanto_rengo_ob_network', 'mc_kanto_rengo_ob',
     'lore', '2014-2024',
     '関東連合 OB ネットワーク — 多方向への離散',
     '関東連合解散(2014)後、元メンバーは個別のビジネス・人脈で活動継続。'
     '一部は実業界・芸能界に進出、一部は指定暴力団系列へ合流、'
     '一部は新型組織犯罪の指示役に転じたと報じられた。'
     '解散しても人脈が残る半グレ特有の構造。',
     None, None, None, '解体後', '半グレ', 4),

    ('ex_yakuza_to_tokuryu', 'mc_ex_yakuza_tokuryu',
     'lore', '2020-',
     '元組員のトクリュウ流入',
     '指定暴力団離脱者の一部がトクリュウ型犯罪の指示役・組成役として関与する '
     '事案が複数報じられた。'
     '工藤會頂上作戦などで組織を出た元構成員が、'
     '新型組織犯罪の人材源となる構図が浮かんだ。',
     None, None, None, '解体後', 'トクリュウ', 4),

    # ===== 沖縄 =====
    ('okinawa_kyokuryukai_main', 'mc_okinawa_kyokuryu',
     'merger', '1949',
     '旭琉会 結成 — 戦後沖縄ヤクザ史の起点',
     '1949年、沖縄那覇で旭琉会が結成。米軍統治下の沖縄で '
     '本土とは隔絶した独自の発展経路を辿る。'
     '日本のヤクザ系統の中で最も独特な歴史背景を持つ組織の一つ。',
     None, None, None, '戦後闇市', '司法側', 4),

    ('okinawa_kyokuryukai_main', 'mc_okinawa_kyokuryu',
     'designation', '1992-1993',
     '旭琉会 指定暴力団指定',
     '本土復帰後の暴対法施行(1992)で、旭琉会も指定暴力団に。'
     '工藤連合草野一家(後の工藤會)と同時期の指定。',
     None, None, None, '高度成長', '司法側', 3),

    ('okinawa_us_military_yakuza', 'mc_us_military_yakuza',
     'lore', '1950s-1972',
     '米軍統治下の沖縄ヤクザ',
     '米軍統治時代の沖縄(1945-1972)では、本土とは隔絶した経済構造の下で '
     'ヤクザ系列が発展。基地周辺の物資ヤミ取引・米兵相手の事業など、'
     '本土にない母体を持っていた。',
     None, None, None, '戦後闇市', '司法側', 3),

    ('koza_okinawa', 'mc_koza_okinawa_book',
     'lore', '1950s-1970s',
     'コザ(沖縄市)— 米軍基地と歓楽街文化',
     'コザ市(現・沖縄市)は嘉手納基地周辺の歓楽街。'
     '米兵相手の商売とヤクザの関係が独特の文化を形成し、'
     '本土復帰前後の沖縄ヤクザ史の中心地として報道書籍に頻出する。',
     None, None, None, '高度成長', '司法側', 3),

    # ===== 京都 =====
    ('kyoto_aizukotetsu_hq', 'mc_aizukotetsu_book',
     'merger', '1869',
     '会津小鉄会 — 明治期創設の長い歴史',
     '1869年(明治2年)創設の会津小鉄会は日本最古級のヤクザ系統。'
     '京都を本拠に関西地場連合体として現代まで継続。'
     '工藤會の戦後闇市出自(1947)とは出自・年代が大きく異なる。',
     None, None, None, '戦後闇市', '司法側', 3),

    ('kyoto_gion', 'mc_kyoto_gion_culture',
     'lore', '1700s-',
     '祇園 — 花街文化と現代の組織犯罪規制',
     '京都の祇園は江戸時代からの伝統花街。'
     '会津小鉄会など関西地場ヤクザの活動エリアの一つで、'
     '伝統文化と暴対法時代の規制が交わる場所として地元紙に '
     '繰り返し取り上げられる。',
     None, None, None, '高度成長', '司法側', 3),

    # ===== 名古屋・弘道会 =====
    ('nagoya_kodokai_hq', 'mc_kodokai_book',
     'merger', '1984',
     '弘道会 結成 — 山口組最大2次団体',
     '1984年、名古屋で弘道会が結成。六代目山口組の最大2次団体となり、'
     '司忍(現組長)が弘道会会長を兼ねた組長。'
     '日本のヤクザ史の中核組織の一つ。',
     None, None, None, '高度成長', '山口組系', 4),

    ('nagoya_sakae_district', 'mc_nagoya_sakae',
     'lore', '1990s-',
     '名古屋 栄 — 中部最大歓楽街と組',
     '名古屋市中区栄。中部地方最大の歓楽街で、'
     '弘道会・他の指定暴力団系列の縄張りが交錯。'
     '小倉の堺町・東京の歌舞伎町と並ぶ「地方主要都市の歓楽街と組」 '
     'の典型例。',
     None, None, None, '高度成長', '山口組系', 3),

    # ===== 大阪 =====
    ('osaka_minami_yakuza', 'mc_osaka_minami_book',
     'lore', '1950s-',
     '大阪ミナミ — 関西地場ヤクザ集中地',
     '大阪市中央区ミナミ(難波・道頓堀周辺)は関西最大の歓楽街。'
     '山口組系・酒梅組・複数地場組織の縄張りが集中する '
     '関西組織犯罪史の中心地。',
     None, None, None, '高度成長', '山口組系', 3),

    ('osaka_kita_yakuza', 'mc_osaka_minami_book',
     'lore', '1950s-',
     '大阪キタ(梅田)— ビジネス街と組',
     '大阪市北区(梅田・北新地)は関西経済の中枢。'
     '山口組系の経済活動の拠点でもあり、伝統的ヤクザの '
     '「フロント企業ライン」が走った場所として報道書籍に描かれる。',
     None, None, None, '高度成長', '山口組系', 3),

    ('osaka_kamagasaki', 'mc_kamagasaki_book',
     'lore', '1960s-',
     '釜ヶ崎(あいりん地区)— 日雇い労働者街と戦後史',
     '大阪市西成区の釜ヶ崎(あいりん地区)は日本最大級の日雇い労働者街。'
     '戦後の労働者文化と組織犯罪の交点として、戦後ヤクザ史研究の重要な参照点。'
     '北九州の八幡製鐵所周辺と並ぶ「重工業都市と労働者街の文化」の代表例。',
     None, None, None, '高度成長', '市民側', 3),
]


LORE = [
    (2500, 'shinagawa_yamiarbeit_2024', '2023-2024',
     '関東広域強盗 — 1都8県への拡散',
     '2023年9月以降の連続強盗事件は、東京・神奈川・千葉・埼玉・茨城・栃木・群馬・'
     '新潟・福島の関東+周辺県に拡散。'
     '従来の指定暴力団の縄張り構造とは無関係に、'
     '「ある県を狙う指示」だけで広域に被害が発生する構図が示された。',
     5, '解体後', 'トクリュウ', 'mc_kanagawa_robbery'),

    (2510, 'osaka_robbery_tokuryu', '2023-2024',
     '関西・中部への拡散 — 山口組地場でも',
     '関東中心だったトクリュウ強盗が大阪・名古屋・神戸にも拡散。'
     '山口組地場の関西でも発生した事実は、'
     '伝統的指定暴力団の縄張りが「現代型組織犯罪」を抑止しない '
     '構造を示した事例として議論された。',
     5, '解体後', 'トクリュウ', 'mc_osaka_tokuryu'),

    (2520, 'tochigi_oyama_robbery', '2023-10',
     '栃木県小山事件 — 強盗致死の現実',
     '2023年10月、栃木県小山市の高齢者宅強盗で被害者が死亡。'
     'トクリュウ型犯罪が「軽い闇バイト」ではなく '
     '殺人罪を含む重大犯罪に直結する現実を示した事案。'
     '実行役の量刑は強盗致死で長期刑となった。',
     5, '解体後', 'トクリュウ', 'mc_tochigi_oyama'),

    (2530, 'kanto_rengo_ob_network', '2014-2024',
     '関東連合 OB — 「解散しても残るネットワーク」',
     '関東連合 解散後10年で、元メンバーは芸能界・実業界・地下経済の '
     '複数領域に分散。'
     '組織としては消滅したが、人脈は半グレ特有の「ゆるい連合」 '
     'として残り、トクリュウ事件の指示役供給源の一つになったと報じられた。',
     4, '解体後', '半グレ', 'mc_kanto_rengo_ob'),

    (2540, 'ex_yakuza_to_tokuryu', '2020s',
     '元組員のセカンドキャリア — 別の組織犯罪へ',
     '指定暴力団の規制強化(暴対法・暴排条例・反社チェック)で組を抜けた '
     '元組員の一部が、トクリュウ型犯罪に新たな居場所を見出す事案。'
     '伝統的「組」が縛れない流動型組織は、'
     '元組員の経験値を取り込む構造を内包する。',
     4, '解体後', 'トクリュウ', 'mc_ex_yakuza_tokuryu'),

    (2550, 'okinawa_kyokuryukai_main', '1949-2024',
     '旭琉会 75年 — 米軍統治・本土復帰・暴対法の三段階',
     '旭琉会は1949年結成から75年。米軍統治下の発展(1949-1972)、'
     '本土復帰後の指定暴力団化(1992)、暴対法時代の縮小、と '
     '三段階の歴史を辿った。日本のヤクザ系統で最も独特な経路。',
     4, '解体後', '司法側', 'mc_okinawa_kyokuryu'),

    (2560, 'kyoto_gion', '1700s-2020s',
     '祇園 vs 堺町 — 伝統花街 vs 戦後歓楽街',
     '京都の祇園(江戸時代から)と小倉の堺町(戦後発展)は、'
     '日本の歓楽街文化の二つの典型。'
     '前者は伝統文化と地場組織、後者は重工業労働者街と地場連合体 — '
     '組織犯罪文化の地理的多様性を示す対比。',
     3, '高度成長', '司法側', 'mc_kyoto_gion_culture'),

    (2570, 'nagoya_kodokai_hq', '1984-2024',
     '弘道会 40年 — 山口組の重心移動',
     '1984年結成の弘道会は40年で六代目山口組の最大2次団体に。'
     '山口組の組織重心が神戸から名古屋へ実質的に移動した経過。'
     '工藤會の田中組分裂と対照的に、組織内で「成長する2次団体」が '
     '本体を支える構図。',
     4, '解体後', '山口組系', 'mc_kodokai_book'),

    (2580, 'osaka_kamagasaki', '1960s-2020s',
     '釜ヶ崎 vs 八幡 — 二つの重工業労働者街',
     '大阪の釜ヶ崎と北九州の八幡製鐵所周辺は、'
     '戦後日本の「労働者街と組織犯罪」の二大典型。'
     '前者は日雇い労働の街として、後者は重工業労働者の街として、'
     'ヤクザ系列の経済的基盤を提供した。',
     4, '高度成長', '市民側', 'mc_kamagasaki_book'),

    (2590, 'ulu_atm_demand', '2020-2024',
     '出し子・受け子 — 「使い捨て」の若者層',
     '出し子・受け子は SNS 闇バイト経由で集められる若者層。'
     '指示役の側からは「使い捨て」の存在として扱われる構図が、'
     '捜査・報道で繰り返し示された。'
     '若者の経済的困窮と犯罪組成の接続が社会問題化。',
     4, '解体後', 'トクリュウ', 'mc_atm_uketakedashi'),

    (2600, 'roman_sagi_online', '2018-2024',
     'ロマンス詐欺 — 国際的組成の新型',
     'マッチングアプリ・SNS 経由のロマンス詐欺は、国内外の '
     '実行役が連携する国際的組成。'
     '被害は年間100億円規模に達し、トクリュウ型犯罪の主要収入源 '
     'の一つになった。',
     4, '解体後', 'トクリュウ', 'mc_roman_sagi_book'),

    (2610, 'tokyo_sns_recruiter_office', '2024-',
     'SNS 募集側摘発 — 戦略転換',
     '2024年以降の警察は、実行役だけでなく募集投稿の作成・発信側を狙う '
     '戦略を強化。Telegram・X(旧Twitter)・LINE グループの分析で、'
     '指示役 → 募集役 → 実行役の連鎖を断ち切る取り組みが進展。',
     3, '解体後', 'トクリュウ', 'mc_sns_recruiter'),
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
    print(f'phase24_more_cases: +{ev_inserted} events, +{lr_inserted} lore')
    if missing: print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
