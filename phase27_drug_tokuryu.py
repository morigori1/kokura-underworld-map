"""Phase 27: 薬物 + トクリュウ 重点深掘り。

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    # 薬物関連
    ('dr_hiropon_book', 'book', '厚生労働省 / 報道書籍',
     '日本の覚せい剤戦後史 — 第一次・第二次流行', None, '1945-1985'),
    ('dr_hiropon_law_1951', 'legislative_record', '国会',
     '覚せい剤取締法 成立(1951)', 'https://kokkai.ndl.go.jp/', '1951-06'),
    ('dr_meth_1990s_book', 'book', '報道書籍',
     '覚せい剤 第二次流行と指定暴力団', None, '1975-1985'),
    ('dr_iranian_dealers', 'news', '朝日新聞 / 警視庁',
     '渋谷・新宿 イラン人売人問題報道', None, '1990s'),
    ('dr_cannabis_history', 'book', '報道書籍',
     '日本の大麻流通史(1990s-)', None, '1990s-'),
    ('dr_dangerous_drugs', 'official_release', '厚生労働省',
     '危険ドラッグ規制強化(2014 薬機法改正)', 'https://www.mhlw.go.jp/', '2014'),
    ('dr_dangerous_drugs_news', 'news', '朝日新聞 / NHK',
     '危険ドラッグ 吸引運転事故 報道(2014)', None, '2014'),
    ('dr_telegram_market', 'news', '日経新聞 / 産経新聞',
     'Telegram 薬物取引拡大 報道(2020s-)', None, '2020-'),
    ('dr_korea_route', 'news', '朝日新聞 / 警察庁',
     '韓国・北朝鮮 薬物密輸ルート報道', None, '1970s-'),
    ('dr_china_se_asia', 'news', '朝日新聞 / Reuters',
     '中国・東南アジア 薬物密輸ルート報道', None, '1990s-'),
    ('dr_yokohama_2019', 'news', '神奈川新聞 / 朝日新聞 / NHK',
     '横浜港 大規模覚せい剤押収報道(2019)', None, '2019'),
    ('dr_npa_yearly', 'police_whitepaper', '警察庁',
     '覚せい剤 検挙状況年次推移', 'https://www.npa.go.jp/', '2010-'),
    ('dr_golden_triangle', 'book', '報道書籍 / Reuters',
     'ゴールデン・トライアングルからの密輸史', None, '1990s-'),

    # トクリュウ関連
    ('to_luffy_court', 'ruling', '東京地方裁判所',
     'ルフィ事件 公判 — 渡邊優樹ら被告', 'https://www.courts.go.jp/', '2023-'),
    ('to_luffy_ruling_2024', 'ruling', '東京地方裁判所',
     'ルフィ事件 殺人罪判決(2024-)', 'https://www.courts.go.jp/', '2024-'),
    ('to_recruiter_takedown', 'news', '朝日新聞 / 警察庁',
     'SNS リクルーター摘発報道(2024)', None, '2024-'),
    ('to_crypto_laundering', 'news', '日経新聞 / 警察庁',
     'トクリュウ 仮想通貨マネロン報道', None, '2020-'),
    ('to_myanmar_compounds', 'news', 'OCCRP / Reuters / 西日本新聞',
     'ミャンマー国境コンパウンド と日本トクリュウ', None, '2022-'),
    ('to_thailand_base', 'news', '朝日新聞 / 共同通信',
     'タイ拠点 日本人指示役 報道', None, '2022-'),
    ('to_jr_route_2024', 'news', '朝日新聞 / NHK',
     'JR 沿線 連続強盗報道(2024)', None, '2024'),
    ('to_young_recruits', 'news', '朝日新聞 / 文部科学省',
     'トクリュウ実行役 若年化問題報道', None, '2023-'),
    ('to_pawn_jewelry', 'news', '朝日新聞 / 警察庁',
     '宝石店・質店襲撃連続報道(2023-2024)', None, '2023-2024'),
    ('to_roman_sagi_intl', 'news', '朝日新聞 / 日経新聞',
     'ロマンス詐欺 国際拠点摘発報道', None, '2018-'),
    ('to_atm_arrests', 'news', '朝日新聞 / 警察庁',
     'ATM 出し子受け子連続逮捕報道(2020s)', None, '2020-'),
    ('to_school_warning', 'official_release', '文部科学省 / 警察庁',
     '学校・自治体 闇バイト予防啓発(2024-)',
     'https://www.mext.go.jp/', '2024-'),
    ('to_korea_tokuryu', 'news', '朝日新聞 / 警視庁',
     '韓国系トクリュウ関連報道', None, '2020-'),
    ('to_compound_japanese', 'news', '西日本新聞 / OCCRP',
     '日本人がコンパウンド被害者として保護される事案', None, '2022-'),
    ('to_npa_white_2024_tokuryu', 'police_whitepaper', '警察庁',
     '令和6年版警察白書 — トクリュウ特集',
     'https://www.npa.go.jp/hakusyo/r06/index.html', '2024'),
]


EVENTS = [
    # ===== 薬物経済 =====
    ('hiropon_first_wave', 'dr_hiropon_book',
     'lore', '1945-1955',
     '第一次覚せい剤流行 — ヒロポン時代',
     '戦後直後、軍事用備蓄の覚せい剤(ヒロポン)が市場流出。'
     '労働者・労組・闇市文化と結びついて第一次流行を形成。'
     '1955年頃まで断続的に蔓延、戦後社会の混乱期の象徴的薬物問題。',
     '一般国民', '中毒', '広範な健康被害', '戦後闇市', '司法側', 5),

    ('hiropon_first_wave', 'dr_hiropon_law_1951',
     'designation', '1951-06',
     '覚せい剤取締法 成立',
     '1951年6月、第10回国会で覚せい剤取締法が成立。'
     'ヒロポン流行への対応として、覚せい剤の所持・使用・販売を罰する '
     '日本の薬物規制の基本枠組みが整備された。',
     None, None, None, '戦後闇市', '司法側', 5),

    ('hiropon_second_wave', 'dr_meth_1990s_book',
     'lore', '1975-1985',
     '第二次覚せい剤流行 — 指定暴力団の組織化',
     '1970年代後半-1980年代の第二次覚せい剤流行。'
     '山口組系・住吉会系など指定暴力団が国内流通を本格的に組織化。'
     '韓国・台湾・香港経由の密輸ルートが確立した時期。',
     '一般国民', '中毒', '広範な被害', '高度成長', '司法側', 5),

    ('iranian_dealers_shibuya', 'dr_iranian_dealers',
     'attack', '1990s-2000s',
     '渋谷・新宿 イラン人売人問題',
     '1990年代-2000年代前半、渋谷・新宿・池袋で '
     'イラン人売人による路上薬物販売が問題化。'
     '指定暴力団とは別系統の組織犯罪として警察庁の特別対策対象に。',
     '一般購入者', '路上密売', '中毒被害', '平成抗争', '司法側', 4),

    ('cannabis_route_history', 'dr_cannabis_history',
     'lore', '1990s-2024',
     '大麻流通の3系統並存',
     '日本の大麻流通は1990年代以降拡大。'
     '指定暴力団系・半グレ系・個人輸入の3系統が並存。'
     '2020年代以降は SNS 経由の小規模取引が増加し、'
     '若年層の使用増加が社会問題化。',
     None, None, None, '解体後', '司法側', 4),

    ('dangerous_drugs_zone', 'dr_dangerous_drugs_news',
     'attack', '2014',
     '危険ドラッグ 吸引運転事故 連続発生',
     '2014年、「脱法ドラッグ」吸引運転事故が連続発生。'
     '渋谷・池袋の販売店摘発が進む。同年薬機法改正で「危険ドラッグ」改称、'
     '指定薬物の包括規制で店舗摘発が一気に進んだ。',
     '一般市民(交通事故被害者)', '薬物吸引運転', '死傷', '頂上作戦', '司法側', 5),

    ('dangerous_drugs_zone', 'dr_dangerous_drugs',
     'designation', '2014',
     '薬機法改正 — 危険ドラッグ規制強化',
     '2014年の薬機法改正で「指定薬物」の包括規制が大幅強化。'
     '販売店舗の摘発・閉鎖が全国規模で進み、'
     '街頭の危険ドラッグ流通はほぼ消滅した。',
     None, None, None, '頂上作戦', '司法側', 4),

    ('drug_korea_route', 'dr_korea_route',
     'lore', '1970s-',
     '韓国・北朝鮮 密輸ルート',
     '戦後日本の覚せい剤密輸の主要ルートの一つ。'
     '海上船便・空港経由の摘発事案が継続的に発生。'
     '北朝鮮製の高純度メタンフェタミンの流通が断続的に報じられた。',
     None, '密輸', None, '高度成長', '司法側', 4),

    ('drug_china_southeast', 'dr_china_se_asia',
     'lore', '1990s-',
     '中国・東南アジア密輸ルート',
     '中国・タイ・カンボジア・ベトナム経由の薬物密輸ルート。'
     'ゴールデントライアングルからの伝統的流通と、'
     '現代のメコンコンパウンド系流通が並存する複合構造。',
     None, '密輸', None, '平成抗争', '司法側', 4),

    ('drug_china_southeast', 'dr_golden_triangle',
     'lore', '1990s-',
     'ゴールデン・トライアングルからの伝統流通',
     'ミャンマー・タイ・ラオス国境地帯の麻薬生産地帯。'
     '日本への密輸経路の終点として戦後継続的に注目されてきた。',
     None, '密輸', None, '高度成長', '司法側', 3),

    ('drug_meth_2019_yokohama', 'dr_yokohama_2019',
     'arrest', '2019',
     '横浜港 大規模覚せい剤押収 — 数百キロ',
     '2019年、横浜港でコンテナ輸送の大規模覚せい剤(報道で数百キロ規模)が押収。'
     '海上保安庁・税関・警察の合同摘発として全国的に報じられた。'
     '指定暴力団系の国際密輸ネットワークの摘発事例。',
     '社会(健康被害想定)', '密輸', '組関係者逮捕', '頂上作戦', '司法側', 5),

    ('drug_2020s_busts', 'dr_npa_yearly',
     'arrest', '2020-2024',
     '2020年代 大規模摘発(継続)',
     '2020年代以降も大規模摘発が継続。'
     'コロナ禍以降の国際物流変化で密輸経路が複雑化。'
     '指定暴力団・トクリュウ系・半グレ系の流通が混在。',
     None, '密輸・流通', '組関係者逮捕', '解体後', '司法側', 3),

    ('drug_telegram_market', 'dr_telegram_market',
     'lore', '2020-',
     'Telegram 薬物取引 — オンライン闇市場の台頭',
     '2020年代、Telegram など匿名 SNS での薬物取引が拡大。'
     '指定暴力団・半グレ・トクリュウ・個人売買が混在するオンライン闇市場の形成。'
     '従来の街頭密売から大きく変質。',
     None, 'SNS密売', None, '解体後', 'トクリュウ', 4),

    # ===== トクリュウ 個別深掘り =====
    ('luffy_court_proceedings', 'to_luffy_court',
     'ruling', '2023-',
     'ルフィ事件 公判進行(東京地裁)',
     '東京地裁での渡邊優樹ら被告の公判。'
     '指示役と実行役の関係立証、SNS 証拠の刑事法的扱いが争点。'
     'トクリュウ型犯罪の司法的位置づけの先例形成事案。',
     None, None, '公判中', '解体後', 'トクリュウ', 5),

    ('luffy_satsumitsu_court', 'to_luffy_ruling_2024',
     'ruling', '2024-',
     'ルフィ事件 — 強盗殺人罪判決進行',
     'ルフィ事件関連被告に対する強盗殺人罪・組織犯罪処罰法違反等の判決進行中。'
     '量刑は無期懲役以上が想定され、指示役4人の責任配分が論点。'
     '日本のトクリュウ司法対応の基準形成事案。',
     None, None, '無期相当', '解体後', '司法側', 5),

    ('tokuryu_recruiter_takedown', 'to_recruiter_takedown',
     'arrest', '2024',
     'SNS リクルーター 大規模摘発(警視庁)',
     '2024年、警視庁が東京都内の SNS 闇バイト募集側を大規模摘発。'
     '指示役 → 募集役 → 実行役の連鎖を断ち切る戦略。'
     '従来の実行役中心の摘発から、組成側を狙う方針転換。',
     '社会(将来被害防止)', 'SNS募集', '組成役逮捕', '解体後', 'トクリュウ', 4),

    ('tokuryu_crypto_laundering', 'to_crypto_laundering',
     'lore', '2020-',
     'トクリュウ 仮想通貨マネロン経路',
     'トクリュウ事件の資金流通で仮想通貨(暗号資産)を介した '
     'マネーロンダリング経路が報じられた。'
     '従来の現金 → SNS募集 → 仮想通貨送金 → 海外換金 への進化。'
     '金融庁・警察庁の仮想通貨取引所監視の強化背景。',
     None, '仮想通貨', None, '解体後', 'トクリュウ', 4),

    ('myanmar_compounds_link', 'to_myanmar_compounds',
     'lore', '2022-',
     'ミャンマー国境コンパウンド — 日本トクリュウとの接続',
     'ミャンマー・タイ国境のコンパウンド群が日本トクリュウの指示拠点として '
     '2022年以降注目。本マップの姉妹プロジェクト Compound Time Machine が詳述。',
     None, None, None, '解体後', 'トクリュウ', 4),

    ('thailand_tokuryu_base', 'to_thailand_base',
     'lore', '2022-',
     'タイ拠点 — 日本人指示役の分散',
     'タイ・バンコク・パタヤ等で日本人指示役が活動拠点を移すケース。'
     'フィリピン入管摘発(ルフィ事件)後の指示役分散化の動き。',
     None, None, None, '解体後', 'トクリュウ', 3),

    ('jr_route_robbery_2024', 'to_jr_route_2024',
     'attack', '2024',
     'JR 沿線 連続強盗事件',
     '2024年、JR 主要路線沿線(中央線・常磐線・武蔵野線等)での連続強盗事件。'
     'アクセスのよさが標的選定の基準になった可能性が捜査で指摘された。',
     '高齢者・店主', '鈍器・刃物', '死傷', '解体後', 'トクリュウ', 4),

    ('tokuryu_young_recruits', 'to_young_recruits',
     'lore', '2023-2024',
     'トクリュウ実行役 — 若年化問題の深刻化',
     '2023-2024 連続強盗事件で逮捕された実行役には大学生・高校生・10代の若者が多数。'
     '貧困・SNS への露出・ホワイトな募集の偽装が組み合わさり、'
     '若年層への被害が社会問題化。',
     '実行役の若者', 'SNS募集→犯罪強要', '長期刑', '解体後', 'トクリュウ', 5),

    ('tokuryu_pawn_jewelry_route', 'to_pawn_jewelry',
     'attack', '2023-2024',
     '宝石店・質店襲撃 連続(関東中心)',
     '2023-2024 宝石店・質店・両替店への襲撃事件が連続。'
     '昼間の都心商業地での襲撃が衝撃を呼んだ。'
     '現金保管の小規模店舗を狙うトクリュウ型犯行の典型。',
     '店舗経営者・店員', '集団暴力', '負傷・物損', '解体後', 'トクリュウ', 4),

    ('roman_sagi_centers', 'to_roman_sagi_intl',
     'attack', '2018-',
     'ロマンス詐欺 — 国際拠点の連続摘発',
     'マッチングアプリ・SNS 経由のロマンス詐欺で、'
     'タイ・カンボジア・ナイジェリア・ガーナの拠点が連続摘発。'
     '被害額は年間100億円規模に達した報告も。',
     '出会い系利用者', '詐欺', '金銭被害', '解体後', 'トクリュウ', 4),

    ('atm_uketakedashi_arrests', 'to_atm_arrests',
     'arrest', '2020-2024',
     'ATM 出し子・受け子 連続逮捕',
     '特殊詐欺・トクリュウ事件で ATM 現金引き出し役・受け取り役の連続逮捕。'
     '若年層の関与が継続的に社会問題化、'
     '銀行業界の ATM 監視強化と並行する動き。',
     '実行役の若者', None, '逮捕', '解体後', 'トクリュウ', 3),

    ('school_predator_warning', 'to_school_warning',
     'designation', '2024-',
     '学校・自治体 闇バイト予防啓発の全国展開',
     '2024年以降、全国の学校・自治体で闇バイト予防啓発が急速に拡大。'
     '文部科学省・警察庁の連携で「ホワイトな高額バイト」募集が '
     '若者を狙う構図への警告キャンペーンが展開された。',
     None, None, None, '解体後', '市民側', 4),

    ('tokuryu_kankoku_link', 'to_korea_tokuryu',
     'lore', '2020-',
     '韓国系トクリュウ — 日韓越境組織犯罪',
     '韓国系の指示役・実行役の関与が報じられた事案が継続。'
     '日韓越境の組織犯罪として警察庁・海上保安庁が継続的に対応。',
     None, None, None, '解体後', 'トクリュウ', 3),

    ('cambodia_compounds_link', 'to_compound_japanese',
     'lore', '2022-',
     'カンボジアコンパウンド — 日本人被害者保護事案',
     '2022年以降、カンボジア・ミャンマーのコンパウンドから日本人被害者を '
     '保護する事案が複数報じられた。'
     '実行役として勧誘された日本人が監禁労働を強いられる構図。'
     '加害者の組織と被害者の若者層の双方が日本人という新型構造。',
     '若年層日本人', '監禁労働', '保護', '解体後', 'トクリュウ', 5),

    ('npa_tokuryu_office', 'to_npa_white_2024_tokuryu',
     'lore', '2024',
     '令和6年版 警察白書 — トクリュウ大特集',
     '令和6年版警察白書はトクリュウを大規模特集。'
     '工藤會のような伝統的指定暴力団とは別系統の現代型組織犯罪として、'
     '今後の捜査・規制の主要テーマとして位置づけられた。'
     'トクリュウ概念の公式定着の節目。',
     None, None, None, '解体後', '司法側', 5),
]


LORE = [
    (4000, 'hiropon_first_wave', '1945-1955',
     'ヒロポン — 戦後混乱期の象徴的薬物',
     '戦後直後のヒロポン流行は、軍事用備蓄の市場流出という '
     '極めて異常な発生経路を持つ。'
     '労働者の長時間労働補助・闇市文化と結びついて広範に蔓延し、'
     '1951年の覚せい剤取締法成立につながった戦後社会史の重要事件。',
     5, '戦後闇市', '司法側', 'dr_hiropon_book'),

    (4010, 'hiropon_second_wave', '1975-1985',
     '第二次覚せい剤流行 — 暴対法の隠れた前史',
     '1970年代後半-1980年代の第二次覚せい剤流行は、'
     '指定暴力団の経済基盤として大きな役割を果たした。'
     '山一抗争(1985-1989)と並んで、暴対法(1991)成立の隠れた前史。',
     4, '高度成長', '司法側', 'dr_meth_1990s_book'),

    (4020, 'dangerous_drugs_zone', '2010-2014',
     '危険ドラッグ — 法と化学の追いかけっこ',
     '2010-2014年の危険ドラッグ(脱法ドラッグ)問題は、'
     '化学構造を変えて規制を逃れる薬物と、規制法の追いかけっこ。'
     '2014年の薬機法改正で「指定薬物」包括規制が導入され、'
     '街頭流通はほぼ消滅した。',
     4, '頂上作戦', '司法側', 'dr_dangerous_drugs'),

    (4030, 'drug_telegram_market', '2020-2024',
     'Telegram 薬物市場 — 街頭から SNS へ',
     '2020年代の薬物流通は街頭密売から SNS 経由へ大きく変化。'
     'Telegram のグループチャット・X(旧Twitter)の隠語投稿・LINE での個別交渉など、'
     '匿名性の高いプラットフォームが流通経路の主流に。'
     '従来の指定暴力団系の街頭ネットワークが弱体化した代替経路。',
     5, '解体後', 'トクリュウ', 'dr_telegram_market'),

    (4040, 'drug_meth_2019_yokohama', '2019',
     '横浜港押収 — 数百キロの覚せい剤',
     '2019年の横浜港大規模押収は、戦後最大級の単発押収事案の一つ。'
     '指定暴力団系の国際密輸ネットワークが摘発された事例で、'
     '海上輸送による大量密輸が依然として続いている事実が示された。',
     5, '頂上作戦', '司法側', 'dr_yokohama_2019'),

    (4050, 'luffy_satsumitsu_court', '2024-',
     'ルフィ事件 判決 — トクリュウ司法の先例形成',
     'ルフィ事件の判決は、トクリュウ型犯罪に対する日本司法の対応の '
     '先例形成事案。指示役4人の責任配分・SNS 証拠の扱い・'
     '海外拠点からの指示の法的位置づけが争点となり、'
     '今後のトクリュウ型犯罪の量刑基準を作る判決となる見込み。',
     5, '解体後', 'トクリュウ', 'to_luffy_ruling_2024'),

    (4060, 'tokuryu_recruiter_takedown', '2024-',
     'SNS リクルーター摘発 — 戦略転換',
     '2024年の SNS リクルーター摘発は、警察の戦略転換を示す。'
     '実行役を捕まえ続ける従来方針から、組成側(指示役・募集役)を狙う方向へ。'
     'SNS プラットフォーム各社との連携、AI 検出技術の活用が進展。',
     5, '解体後', 'トクリュウ', 'to_recruiter_takedown'),

    (4070, 'tokuryu_crypto_laundering', '2020-',
     'トクリュウ仮想通貨マネロン — 現代型流通',
     'トクリュウの資金流通は SNS 募集 → 仮想通貨送金 → 海外換金 という '
     '現代型マネロン構造。従来の現金主体の組織犯罪資金とは大きく異なり、'
     '金融庁の仮想通貨取引所監視の強化に直結する課題。',
     5, '解体後', 'トクリュウ', 'to_crypto_laundering'),

    (4080, 'cambodia_compounds_link', '2022-',
     'カンボジア — 加害者と被害者の二重構造',
     'カンボジアのコンパウンドから日本人被害者を保護する事案は、'
     'トクリュウの新しい二重構造を示す。'
     '実行役として勧誘された日本人若者が現地で監禁労働を強いられ、'
     '加害者(指示役)と被害者(実行役)の双方が日本人という構図。',
     5, '解体後', 'トクリュウ', 'to_compound_japanese'),

    (4090, 'tokuryu_young_recruits', '2023-2024',
     '若年実行役 — 「使い捨て」と「捨て駒」の構造',
     '2023-2024 連続強盗事件の実行役は大学生・高校生・10代の若者が多数。'
     '貧困・SNS への露出・「ホワイトな高額バイト」の偽装募集が組み合わさり、'
     '指示役からは「捨て駒」扱いされる構図が捜査で示された。'
     '伝統的指定暴力団の盃事による縦の結束は皆無、'
     '冷たい現代型組織犯罪の本質。',
     5, '解体後', 'トクリュウ', 'to_young_recruits'),

    (4100, 'tokuryu_pawn_jewelry_route', '2023-2024',
     '宝石店襲撃 — 昼間都心襲撃の衝撃',
     '2023-2024 宝石店襲撃事件は、昼間の都心商業地で発生する集団襲撃。'
     '従来の戸建て高齢者宅(深夜・郊外)とは異なる、より大胆で衝撃的な手口。'
     '社会の安全感の根幹を揺るがす事案として議論された。',
     5, '解体後', 'トクリュウ', 'to_pawn_jewelry'),

    (4110, 'roman_sagi_centers', '2018-2024',
     'ロマンス詐欺 — 国際組成の新型',
     'ロマンス詐欺は、マッチングアプリ・SNS 経由の出会いから始まり、'
     '海外指示役 → 国内仲介者 → 被害者の構造で組成される国際型詐欺。'
     '被害額の積み上げ・恋愛感情の利用という特殊な攻撃手法。'
     '被害者支援の困難さも問題化。',
     5, '解体後', 'トクリュウ', 'to_roman_sagi_intl'),

    (4120, 'school_predator_warning', '2024-',
     '学校での闇バイト予防 — 社会全体の教育課題',
     '2024年以降、全国の学校・自治体で闇バイト予防啓発が急速に拡大。'
     '高校・大学のキャリア教育に組み込まれ、'
     '「楽な高額バイト」が罠であることを若者に伝える教育が制度化された。'
     'トクリュウ問題が個別事件対応から社会教育レベルに格上げされた節目。',
     4, '解体後', '市民側', 'to_school_warning'),

    (4130, 'iranian_dealers_shibuya', '1990s-2000s',
     'イラン人売人 — 90年代渋谷の風景',
     '1990年代の渋谷・新宿の路上で「イラン人売人」が立つ風景は、'
     '当時の都市の現代史の一部だった。'
     '日本人指定暴力団とは別系統の路上薬物販売者として、'
     '警察庁の特別対策対象だった時代。',
     4, '平成抗争', '司法側', 'dr_iranian_dealers'),

    (4140, 'drug_korea_route', '1970s-2024',
     '韓国・北朝鮮ルート — 50 年の継続',
     '韓国・北朝鮮経由の覚せい剤密輸ルートは戦後50年以上継続。'
     '海上船便・空港・コンテナ密輸の摘発事案が断続的に発生。'
     '北朝鮮製の高純度メタンフェタミンは現在も流通の一部と報じられる。',
     4, '解体後', '司法側', 'dr_korea_route'),

    (4150, 'myanmar_compounds_link', '2022-',
     'ミャンマー国境 — トクリュウと国家崩壊',
     'ミャンマー国境地帯のコンパウンドは、ミャンマーの政治混乱・国家機能崩壊の '
     '空白に立地。日本のトクリュウ犯罪の海外拠点として機能する事実は、'
     '国際組織犯罪と地政学的不安定の連結を示す。',
     5, '解体後', 'トクリュウ', 'to_myanmar_compounds'),

    (4160, 'thailand_tokuryu_base', '2023-',
     'タイ — フィリピン以後の分散先',
     'ルフィ事件後、日本人指示役の拠点はフィリピンからタイ・カンボジア・'
     'マレーシア等に分散したと報じられた。'
     '一カ所摘発したら別の国へ移る組織犯罪の流動性。',
     4, '解体後', 'トクリュウ', 'to_thailand_base'),

    (4170, 'atm_uketakedashi_arrests', '2020-2024',
     'ATM 監視 vs 出し子の追いかけっこ',
     '銀行業界の ATM 監視強化(限度額引下げ・本人確認強化)と、'
     'トクリュウ系の出し子・受け子の手口進化の追いかけっこが続いている。'
     '銀行・警察・SNS の三者連携が深化。',
     3, '解体後', 'トクリュウ', 'to_atm_arrests'),

    (4180, 'jr_route_robbery_2024', '2024',
     'JR 沿線標的 — 「アクセスの良さ」が選定基準',
     '2024年の連続強盗事件では、JR 主要路線沿線の標的選定が捜査で指摘された。'
     '実行役の交通アクセス・逃走経路を考慮した指示役の標的選定の合理性。',
     4, '解体後', 'トクリュウ', 'to_jr_route_2024'),
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
    print(f'phase27_drug_tokuryu: +{ev_inserted} events, +{lr_inserted} lore')
    if missing: print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
