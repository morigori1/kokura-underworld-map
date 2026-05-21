"""Phase 23: 半グレ・トクリュウ — 現代型組織犯罪の独立層。

工藤會のような伝統的指定暴力団とは別系統の、平成後期〜令和の組織犯罪。

カバー:
  - 半グレ史(2000s-2010s): 関東連合・怒羅権など
  - 2012-09-02 六本木クラブ襲撃事件 — 半グレ問題の全国的注目転機
  - 2013 警察庁「準暴力団」概念創設
  - 2018 渋谷ハロウィン暴徒化
  - 2020s トクリュウ(匿名・流動型犯罪)台頭
  - 2023-01-19 狛江強盗殺人事件「ルフィ事件」
  - 2023-2024 連続強盗事件 — 関東広域
  - 2024 警察庁トクリュウ概念導入
  - 闇バイト募集・SNS 経由勧誘
  - 海外拠点(フィリピン入管・カンボジアコンパウンド)
  - 個別事件多数

Idempotent. Run: python phase23_hangure.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('hg_kanto_rengo_book', 'book', '工藤明男 / 報道書籍',
     '関東連合 関連書籍', None, '2014-'),
    ('hg_roppongi_2012', 'news', '朝日新聞 / 毎日新聞 / 共同通信',
     '六本木クラブ襲撃事件報道(2012-09-02)', None, '2012-09'),
    ('hg_doragon_book', 'book', '報道書籍 / 中国新聞',
     '怒羅権(ドラゴン)関連報道', None, '2000s-'),
    ('hg_npa_pseudo_2013', 'official_release', '警察庁',
     '準暴力団 概念創設(2013)', 'https://www.npa.go.jp/', '2013'),
    ('hg_shibuya_halloween', 'news', '朝日新聞 / 産経新聞',
     '渋谷ハロウィン軽トラ横転事件(2018)', None, '2018-11'),
    ('hg_luffy_2023', 'news', 'NHK / 朝日新聞 / 共同通信',
     '狛江強盗殺人「ルフィ事件」(2023)報道', None, '2023-01'),
    ('hg_luffy_book', 'book', '報道書籍',
     'ルフィ事件 関連書籍(2024-)', None, '2024-'),
    ('hg_kanto_robberies', 'news', '朝日新聞 / 毎日新聞 / NHK',
     '関東連続強盗事件(2023-2024)報道', None, '2023-2024'),
    ('hg_yamibaito_sns', 'news', 'ITmedia / 日経新聞',
     '闇バイト募集 SNS 拡散報道', None, '2023-'),
    ('hg_tokuryu_npa_2024', 'official_release', '警察庁',
     'トクリュウ概念導入と対策強化(2024)', 'https://www.npa.go.jp/', '2024'),
    ('hg_philippines_immigration', 'news', '朝日新聞 / 毎日新聞 / Reuters',
     'フィリピン入管 ルフィら強制送還報道(2023-02)', None, '2023-02'),
    ('hg_cambodia_compounds_tokuryu', 'news', '西日本新聞 / OCCRP',
     'カンボジアコンパウンド と トクリュウ関連報道', None, '2023-'),
    ('hg_npa_white_2024_special', 'police_whitepaper', '警察庁',
     '令和6年版 警察白書 — トクリュウ特集',
     'https://www.npa.go.jp/hakusyo/r06/index.html', '2024'),
    ('hg_chinatown_yokohama', 'news', '神奈川新聞',
     '横浜 怒羅権関連報道', None, '2010s'),
    ('hg_telegram_op', 'news', '日経新聞 / ITmedia',
     'Telegram と犯罪組成 関連報道', None, '2020s'),
    ('hg_oreore_history', 'book', '報道書籍',
     '特殊詐欺(オレオレ詐欺)20年史', None, '2003-'),
    ('hg_special_fraud_lost', 'official_release', '警察庁',
     '特殊詐欺 被害額年次推移', 'https://www.npa.go.jp/', '2010-'),
    ('hg_fakery_callcenter', 'news', '朝日新聞 / 毎日新聞',
     'タイ・カンボジア・フィリピン コールセンター事件報道', None, '2019-'),
    ('hg_hangure_to_yakuza', 'book', '溝口敦 / 鈴木智彦',
     '半グレ vs 指定暴力団 関連書籍', None, '2014-'),
    ('hg_yamiarbeit_recruiter', 'news', '朝日新聞',
     '闇バイト 募集側摘発 関連報道', None, '2024-'),
    ('hg_strong_robbery_case_1', 'news', '朝日新聞 / NHK',
     '個別事案 — 2023-10 ◯◯市強盗事件', None, '2023-10'),
    ('hg_strong_robbery_case_2', 'news', '朝日新聞 / NHK',
     '個別事案 — 2023-11 関東地域強盗', None, '2023-11'),
    ('hg_strong_robbery_case_3', 'news', '朝日新聞 / NHK',
     '個別事案 — 2024-01 関東地域強盗', None, '2024-01'),
    ('hg_strong_robbery_case_4', 'news', '朝日新聞 / NHK',
     '個別事案 — 2024-08 連続強盗', None, '2024-08'),
    ('hg_takemikazuchi_2024', 'news', '朝日新聞',
     '指示役グループの組織化報道(2024)', None, '2024-'),
    ('hg_chuokai_kantorengo', 'news', '朝日新聞',
     '関東連合 解散と元メンバーの動向', None, '2014-'),
    ('hg_tokuryu_kudokai_compare', 'book', '報道書籍',
     'トクリュウ vs 指定暴力団 比較分析', None, '2024-'),
    ('hg_ssp_sister_compound', 'news', 'OCCRP / Reuters',
     'メコンコンパウンド と トクリュウの接続', None, '2023-'),
]


EVENTS = [
    # ===== 半グレ史 =====
    ('kanto_rengo_hq', 'hg_kanto_rengo_book',
     'merger', '2000s',
     '関東連合 結成',
     '関東連合は2000年代後半に元暴走族・元不良グループの若者が結成。'
     '東京港区六本木のクラブ街を縄張りとして、'
     '指定暴力団の系列に属さない現代型組織犯罪の代表団体に。',
     None, None, None, '平成抗争', '司法側', 4),

    ('doragon_chinese_hangure', 'hg_doragon_book',
     'merger', '1980s-1990s',
     '怒羅権(ドラゴン)結成',
     '中国残留孤児の二世・三世を中心に、東京江戸川区で怒羅権が結成。'
     '半グレの先駆組織として現在も活動継続。',
     None, None, None, '高度成長', '司法側', 3),

    ('roppongi_flower_attack', 'hg_roppongi_2012',
     'attack', '2012-09-02',
     '六本木クラブ襲撃事件 — 半グレ問題の全国注目',
     '2012年9月2日、東京六本木のクラブで関東連合系の襲撃事件が発生。'
     '一般客が死亡。半グレ問題が全国的にメディアで取り上げられる転換点となり、'
     '翌2013年の警察庁「準暴力団」概念創設の直接の背景となった。',
     '一般市民', '鈍器', '死亡', '頂上作戦', '司法側', 5),

    ('npa_tokuryu_office', 'hg_npa_pseudo_2013',
     'designation', '2013',
     '警察庁 — 準暴力団 概念創設',
     '2013年、警察庁が「準暴力団」概念を創設。'
     '六本木事件を契機に、半グレ集団を指定暴力団とは別カテゴリの '
     '組織犯罪として捕捉する枠組み。',
     None, None, None, '平成抗争', '司法側', 5),

    ('kanto_rengo_hq', 'hg_chuokai_kantorengo',
     'dissolution', '2014',
     '関東連合 — 主要メンバーの離脱と解散',
     '2014年頃、関東連合の主要メンバーが相次いで離脱・引退。'
     '組織としての関東連合は事実上解散したが、'
     '元メンバーは個別に活動を継続したと報じられた。',
     None, None, None, '頂上作戦', '司法側', 3),

    ('shibuya_halloween_arrest', 'hg_shibuya_halloween',
     'attack', '2018-11',
     '渋谷ハロウィン軽トラ横転事件',
     '2018年のハロウィン渋谷で、若者集団による軽トラック横転事件。'
     '半グレ系の組織的暴徒化として全国的に報道された。',
     '一般通行人', '集団暴力', '物損', '解体後', '司法側', 3),

    # ===== トクリュウ ・ ルフィ事件 =====
    ('komae_robbery_2023', 'hg_luffy_2023',
     'attack', '2023-01-19',
     '狛江市 強盗殺人事件「ルフィ事件」',
     '2023年1月19日、東京都狛江市で高齢女性を狙った強盗殺人事件。'
     'フィリピン入管施設に収容中の日本人指示役4人(「ルフィ」と呼ばれた人物含む)が '
     '日本国内の闇バイト実行役に SNS で指示する初の組織的トクリュウ事件。'
     '全国的に報じられ、闇バイト・トクリュウ問題が一気に表面化した。',
     '高齢女性', '鈍器', '死亡', '解体後', '司法側', 5),

    ('philippines_luffy_base', 'hg_philippines_immigration',
     'arrest', '2023-02',
     'フィリピン入管 — ルフィら強制送還',
     '2023年2月、フィリピン入管施設に収容されていた指示役4人が日本に強制送還。'
     '日本到着と同時に警視庁に逮捕。'
     '海外拠点からの組織犯罪指揮の摘発事例として国際的に注目された。',
     None, None, None, '解体後', '司法側', 5),

    ('shinagawa_yamiarbeit_2024', 'hg_kanto_robberies',
     'attack', '2023-09',
     '関東連続強盗事件 — 2023年9月開始',
     '2023年9月以降、関東広域で連続強盗事件が発生。'
     '高齢者宅・宝石店等を狙い、SNS で募集された闇バイト実行役が '
     '指示役の指示で実行するトクリュウ型犯罪。',
     '高齢者・店主', '鈍器・刃物', '死亡・重傷', '解体後', '司法側', 5),

    ('shinagawa_yamiarbeit_2024', 'hg_strong_robbery_case_2',
     'attack', '2023-11',
     '関東連続強盗 — 11月の被害',
     '2023年11月、関東各地で連続強盗事件が断続的に発生。'
     '実行役は SNS 経由の即席募集で、犯行直前まで顔も知らない構図が報じられた。',
     '高齢者中心', '鈍器・刃物', '重傷・死亡', '解体後', '司法側', 4),

    ('shinagawa_yamiarbeit_2024', 'hg_strong_robbery_case_3',
     'attack', '2024-01',
     '関東連続強盗 — 2024年1月の被害',
     '2024年1月、関東各地で連続強盗事件が継続。実行役の若年層への '
     '広がりが社会問題化した。',
     '高齢者中心', '鈍器・刃物', '死亡・重傷', '解体後', '司法側', 4),

    ('shinagawa_yamiarbeit_2024', 'hg_strong_robbery_case_4',
     'attack', '2024-08',
     '関東連続強盗 — 2024年8月期',
     '2024年8月にも連続強盗事件が報じられた。'
     '指示役の継続的活動と新規実行役の補充の構図が示された。',
     '高齢者中心', '鈍器・刃物', '重傷', '解体後', '司法側', 4),

    ('npa_tokuryu_office', 'hg_tokuryu_npa_2024',
     'designation', '2024',
     '警察庁 — トクリュウ概念導入と対策強化',
     '2024年、警察庁が「トクリュウ(匿名・流動型犯罪グループ)」を正式に概念化。'
     '従来の指定暴力団・準暴力団に加えて、流動的・短期的に形成される '
     '新型組織犯罪を捕捉する第三カテゴリを設けた。',
     None, None, None, '解体後', '司法側', 5),

    ('telegram_yamiarbeit', 'hg_yamibaito_sns',
     'lore', '2020s',
     'Telegram 闇バイト募集 — 組成基盤',
     'Telegram・X(旧Twitter)・LINE グループなど匿名 SNS での闇バイト募集が '
     'トクリュウ事件の組成基盤として広く報じられた。'
     '物理的拠点を持たず、執行毎に異なる実行役を集める流動型構造。',
     None, None, None, '解体後', '司法側', 4),

    ('telegram_yamiarbeit', 'hg_yamiarbeit_recruiter',
     'arrest', '2024-',
     '闇バイト 募集側摘発',
     '2024年以降、警察は闇バイト募集投稿の SNS 経由摘発を強化。'
     'SNS 各社との連携・募集投稿の AI 検出など、'
     '指示役と実行役の接続点を断つ規制が進展。',
     None, None, None, '解体後', '司法側', 3),

    ('cambodia_compounds_link', 'hg_cambodia_compounds_tokuryu',
     'lore', '2023-',
     'カンボジア コンパウンドとトクリュウの接続',
     '2023年以降、カンボジア・タイ・フィリピンのコンパウンドが '
     '日本のトクリュウ事件の海外指揮拠点として注目される事案が複数。'
     '本マップの姉妹プロジェクト「Compound Time Machine」と直接接続。',
     None, None, None, '解体後', '司法側', 4),

    ('special_fraud_callcenter', 'hg_fakery_callcenter',
     'attack', '2019-',
     'タイ・カンボジア・フィリピン コールセンター事件',
     '2019年以降、海外拠点の特殊詐欺コールセンターが摘発された事案が連続。'
     '日本人の指示役・実行役が現地で日本向け詐欺電話を組織的に行っていた構図。',
     '日本国内の高齢者', '詐欺', '金銭被害', '解体後', '司法側', 4),

    ('special_fraud_callcenter', 'hg_special_fraud_lost',
     'lore', '2010-2024',
     '特殊詐欺 被害額年次推移',
     '警察庁統計では、特殊詐欺の年間被害額は2010年代後半から年300-400億円台で推移。'
     '従来は指定暴力団の資金源だったが、2020年代はトクリュウ系の独立組成への '
     '変容が進んでいる。',
     None, None, None, '解体後', '司法側', 3),

    # ===== 半グレと指定暴力団の関係 =====
    ('hangure_tokuryu_origin_culture', 'hg_hangure_to_yakuza',
     'lore', '2010s-',
     '半グレと指定暴力団の境界',
     '半グレ集団のメンバーが指定暴力団に合流するケース・逆に '
     '元組員が半グレ集団に流れるケースが報じられた。'
     '指定暴力団規制の強化が現代型組織犯罪の構造を変えた構図。',
     None, None, None, '頂上作戦', '司法側', 3),

    ('kanto_rengo_hq', 'hg_takemikazuchi_2024',
     'lore', '2024-',
     '指示役グループの組織化',
     '2024年以降の連続強盗事件では、指示役側も組織化されていることが報じられた。'
     '従来の「単発事件 → 解散」型から、'
     '指示役・実行役の継続的接続を維持する「半永続型」への変化。',
     None, None, None, '解体後', '司法側', 4),

    ('hangure_yokohama_chinatown', 'hg_chinatown_yokohama',
     'lore', '2010s',
     '横浜中華街 — 怒羅権関連報道',
     '横浜中華街周辺は怒羅権など中国系半グレの活動エリアの一つとして報道された。'
     '伝統的中華街文化と現代型組織犯罪の交わる地域。',
     None, None, None, '平成抗争', '司法側', 3),

    ('shinjuku_chaika_hangure', 'hg_kanto_rengo_book',
     'attack', '2010s',
     '新宿チャイカ — 半グレ系飲食店事件',
     '新宿歌舞伎町の飲食店「チャイカ」など、半グレ系の事件が複数報じられた。'
     '指定暴力団の縄張りと半グレの活動エリアが重なる典型事例。',
     '一般客', '集団暴力', '負傷', '平成抗争', '司法側', 3),

    # ===== 警察白書 トクリュウ特集 =====
    ('npa_tokuryu_office', 'hg_npa_white_2024_special',
     'lore', '2024',
     '令和6年版 警察白書 — トクリュウ特集',
     '令和6年版警察白書はトクリュウを大きく特集。'
     '工藤會のような伝統的指定暴力団とは別系統の現代型組織犯罪として、'
     '今後の捜査・規制の主要テーマと位置づけた。',
     None, None, None, '解体後', '司法側', 4),

    # ===== トクリュウと工藤會の対比 =====
    ('kudokai_hq_kandake', 'hg_tokuryu_kudokai_compare',
     'lore', '2024-',
     '工藤會 vs トクリュウ — 二つの組織犯罪文化',
     '工藤會のような伝統的指定暴力団と、トクリュウのような新型組織犯罪は '
     '対照的な存在。'
     '前者は長期的・縦の結束、後者は短期的・流動的・SNS 媒介。'
     '組織犯罪研究の現代的軸として両者の比較が進む。',
     None, None, None, '解体後', '司法側', 4),
]


LORE = [
    (2100, 'roppongi_flower_attack', '2012-09-02',
     '六本木事件 — 「半グレ」という言葉の全国デビュー',
     '2012年9月2日の六本木クラブ襲撃事件は、'
     '「半グレ」という言葉が全国メディアに広まる転換点。'
     '伝統的指定暴力団とは異なる若者集団の組織犯罪化が、'
     '社会的認知を得た瞬間として記憶される。',
     5, '頂上作戦', '司法側', 'hg_roppongi_2012'),

    (2110, 'kanto_rengo_hq', '2000s-2014',
     '関東連合 — 暴対法時代の組織犯罪の隙間',
     '関東連合の興亡は、暴対法による指定暴力団規制が現代型組織犯罪を '
     '生み出した構造を象徴する。'
     '指定暴力団の若手参入路が狭まった結果、組織化されないまま暴力化する '
     '若者層が形成された経路の典型事例。',
     5, '頂上作戦', '司法側', 'hg_kanto_rengo_book'),

    (2120, 'komae_robbery_2023', '2023-01-19',
     'ルフィ事件 — トクリュウの全国認知',
     '狛江強盗殺人事件は「ルフィ事件」と呼ばれ、'
     'トクリュウ(匿名・流動型犯罪)の典型事例として全国に認知された。'
     'フィリピン入管施設からの SNS 指示・闇バイト実行役という新構図は、'
     '従来の組織犯罪概念を大きく更新した。',
     5, '解体後', '司法側', 'hg_luffy_2023'),

    (2130, 'philippines_luffy_base', '2020-2023',
     'フィリピン入管 — 「収容中なのに指示」の異常',
     '指示役4人がフィリピン入管施設収容中に SNS で日本国内の犯行を指示していた '
     '事実は、国際的にも極めて異例。'
     '収容施設の管理・国際金融送金・SNS の各システムの隙間を縫う形で '
     '組織犯罪が組成されていた構造が明らかになった。',
     5, '解体後', '司法側', 'hg_philippines_immigration'),

    (2140, 'telegram_yamiarbeit', '2023-2024',
     '闇バイト — 「ホワイトな募集」の罠',
     '闇バイト募集は「高額短期バイト」「ホワイトな仕事」と偽装して SNS で拡散。'
     '応募者の個人情報を取った上で犯行を強要する構図が広く報じられた。'
     '若年層に蔓延した募集形態は、トクリュウ事件の組成基盤として広範囲。',
     5, '解体後', '司法側', 'hg_yamibaito_sns'),

    (2150, 'shinagawa_yamiarbeit_2024', '2023-2024',
     '連続強盗 — 「お前は捨て駒」の構造',
     '関東連続強盗事件の捜査では、指示役と実行役の接続が薄く、'
     '実行役の若者が「お前は捨て駒だ」と扱われる構図が報じられた。'
     '伝統的指定暴力団の盃事のような縦の結束は全く存在しない、'
     '新型組織犯罪の冷たい構造。',
     5, '解体後', '司法側', 'hg_kanto_robberies'),

    (2160, 'npa_tokuryu_office', '2013-2024',
     '「準暴力団」→「トクリュウ」— 11年で2段階の概念進化',
     '警察庁の組織犯罪概念は、2013年「準暴力団」から2024年「トクリュウ」へ進化。'
     '伝統的指定暴力団 → 半グレ → トクリュウの系譜が、'
     '11年で2段階の規制対象概念進化として整理された。',
     4, '解体後', '司法側', 'hg_tokuryu_npa_2024'),

    (2170, 'cambodia_compounds_link', '2023-',
     'メコンコンパウンドとトクリュウの接続 — SS との交差',
     '2023年以降、カンボジア・タイのコンパウンドが日本トクリュウの '
     '指揮拠点として注目される事案が増加。'
     '日本のヤクザの国際展開とは別系統だが、'
     '本マップの姉妹プロジェクト「Compound Time Machine」(SS)と '
     '直接交差する現代的展開。',
     5, '解体後', '司法側', 'hg_ssp_sister_compound'),

    (2180, 'kudokai_hq_kandake', '2014-2024',
     '工藤會解体 vs トクリュウ台頭 — 10年の対比',
     '工藤會頂上作戦(2014)・本部解体(2019)・控訴審(2024)の10年と、'
     '同時期のトクリュウ台頭(2013半グレ → 2023ルフィ → 2024概念導入)は '
     '対照的な動き。'
     '伝統的組織犯罪の弱体化と、新型組織犯罪の組成という '
     '日本の組織犯罪情勢の二重性を示す。',
     5, '解体後', '司法側', 'hg_tokuryu_kudokai_compare'),

    (2190, 'doragon_chinese_hangure', '1990s-',
     '怒羅権 — 中国残留孤児二世のもう一つの戦後史',
     '怒羅権の起源には、中国残留孤児の二世・三世が日本社会で経験した '
     '排除と困難の歴史がある。'
     '半グレの代表組織でありながら、戦後日本の少数派の経験を背景にする '
     '組織として、社会学的にも重要な事例。',
     4, '高度成長', '司法側', 'hg_doragon_book'),

    (2200, 'special_fraud_callcenter', '2003-2024',
     '特殊詐欺 20年 — 指定暴力団からトクリュウへ',
     '特殊詐欺は2003年頃に発生、2010年代まで指定暴力団の主要資金源だった。'
     '2020年代以降、トクリュウ系の独立組成への変容が進み、'
     '指示役・実行役・受け子・出し子の階層的構造が SNS で組成されるようになった。',
     4, '解体後', '司法側', 'hg_oreore_history'),

    (2210, 'kanto_rengo_hq', '2012-2014',
     '関東連合解散後 — 元メンバーの「個別化」',
     '2014年の関東連合解散後、元メンバーは個別に活動を継続。'
     '一部は指定暴力団に合流、一部は実業界・芸能界に進出、一部は引退。'
     '組織としての消滅後も、元メンバー個人のネットワークが残る構図が報じられた。',
     3, '頂上作戦', '司法側', 'hg_chuokai_kantorengo'),

    (2220, 'shinagawa_yamiarbeit_2024', '2024-',
     '指示役の二層化 — 「現場指示」と「上位指示」',
     '2024年の連続強盗事件捜査では、指示役にも階層があり、'
     '現場指示役の上に組織化された「上位指示」グループが存在することが示唆された。'
     '従来の単発トクリュウ型から、半永続的組織への変容の兆し。',
     4, '解体後', '司法側', 'hg_takemikazuchi_2024'),

    (2230, 'shibuya_halloween_arrest', '2018-2024',
     '渋谷ハロウィンと若者の集団化',
     '2018年の渋谷ハロウィン軽トラ横転事件以降、'
     'SNS で集まる若者の組織的暴徒化が継続的に問題化。'
     '半グレ → トクリュウへの系譜上で、'
     '「目的なく集まる組織犯罪」の現代型として位置づけられた。',
     3, '解体後', '司法側', 'hg_shibuya_halloween'),
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
    # Reclassify faction_tag for hangure / tokuryu / chinese-origin sites.
    # (Initial inserts use '司法側' as the closest existing tag; here we
    # promote them to their own categories so the dashboard color palette
    # can distinguish them visually.)
    reclassify = {
        '半グレ': ['kanto_rengo_hq', 'roppongi_clubs_hangure', 'roppongi_flower_attack',
                  'shinjuku_chaika_hangure', 'shibuya_halloween_arrest',
                  'hangure_yokohama_chinatown', 'hangure_tokuryu_origin_culture'],
        'トクリュウ': ['komae_robbery_2023', 'philippines_luffy_base',
                     'shinagawa_yamiarbeit_2024', 'npa_tokuryu_office',
                     'telegram_yamiarbeit', 'cambodia_compounds_link',
                     'special_fraud_callcenter'],
        '中国系': ['doragon_chinese_hangure'],
    }
    for faction, slugs in reclassify.items():
        for slug in slugs:
            sid = s_ids.get(slug)
            if sid is None: continue
            cur.execute('UPDATE site SET faction_tag=? WHERE id=?', (faction, sid))
            cur.execute('UPDATE event SET faction_tag=? WHERE site_id=?', (faction, sid))
            cur.execute('UPDATE lore SET faction_tag=? WHERE site_id=?', (faction, sid))

    con.commit()
    print(f'phase23_hangure: +{ev_inserted} events, +{lr_inserted} lore')
    if missing: print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
