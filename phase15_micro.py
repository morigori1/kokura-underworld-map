"""Phase 15: micro events + supplementary lore — year-by-year gap filling.

Adds many smaller events and colorful details to fill the chronological gaps
between the big seeded events. Topics include:
  - Year-by-year status snapshots from 警察白書
  - 傘下組(田中組・極東組・吉竹組ほか)の個別動向
  - 公判の節目(中間期日・証人尋問・控訴提起)
  - 北九州の三大組構図(八幡・小倉・門司)
  - 関連企業・フロント企業
  - 暴排ステッカー普及の年代別推移
  - 解体跡地の活用問題
  - コロナ禍と暴排運動
  - 元組員 YouTube カルチャー
  - 街角に残る組事務所跡

Idempotent. Run: python phase15_micro.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('mc_yawata_kokura_moji', 'book', '山平重樹 / 北九州市史',
     '北九州の三大組構図(八幡・小倉・門司)関連記述', None, '1990s-2010s'),
    ('mc_kobetsu_ji', 'news', '西日本新聞 / 朝日新聞',
     '工藤會傘下個別組事務所の動向報道', None, '2010-2020'),
    ('mc_koban_demolition', 'news', '西日本新聞',
     '神岳本部解体当日の現場ルポ', None, '2019-07'),
    ('mc_kominzu_company', 'news', '西日本新聞 / 産経新聞',
     '工藤會関連企業・フロント企業の報道', None, '2014-2024'),
    ('mc_st_sticker', 'news', '西日本新聞 / 北九州市',
     '暴排ステッカーの普及推移', None, '2010-2024'),
    ('mc_corona_bouhai', 'news', '西日本新聞',
     'コロナ禍と暴排運動の継続', None, '2020-2022'),
    ('mc_court_chukan', 'news', '西日本新聞',
     '工藤會公判の中間期日・証人尋問報道', None, '2015-2021'),
    ('mc_youtube_culture', 'news', 'ITmedia / IT 系メディア',
     '元組員 YouTube チャンネルの隆盛', None, '2018-2024'),
    ('mc_atochi_problem', 'news', '西日本新聞 / 北九州市議会',
     '工藤會本部跡地の活用問題', None, '2019-2024'),
    ('mc_kokurakita_satellite', 'news', '西日本新聞',
     '小倉北区各町の組事務所跡 写真連載', None, '2019-2022'),
    ('mc_npa_2024', 'police_whitepaper', '警察庁',
     '令和6年(2024)版 警察白書 — 暴力団情勢',
     'https://www.npa.go.jp/hakusyo/r06/index.html', '2024'),
    ('mc_npa_2023', 'police_whitepaper', '警察庁',
     '令和5年(2023)版 警察白書 — 暴力団情勢',
     'https://www.npa.go.jp/hakusyo/r05/index.html', '2023'),
    ('mc_npa_2020', 'police_whitepaper', '警察庁',
     '令和2年(2020)版 警察白書 — 工藤會情勢',
     'https://www.npa.go.jp/hakusyo/r02/index.html', '2020'),
    ('mc_npa_2015', 'police_whitepaper', '警察庁',
     '平成27年(2015)版 警察白書 — 頂上作戦総括',
     'https://www.npa.go.jp/hakusyo/h27/index.html', '2015'),
    ('mc_ribetai_book', 'book', '元組員手記出版物',
     '工藤會傘下離脱手記', None, '2018-'),
    ('mc_kokura_keisatsu_serial', 'news', '西日本新聞',
     '北九州警察ノンフィクション連載 — 組対課の日常', None, '2015-'),
    ('mc_court_supreme', 'ruling', '最高裁判所',
     '工藤會関連 上告審進行(2024-)', 'https://www.courts.go.jp/', '2024-'),
    ('mc_kuyakushotsuki_serial', 'news', '西日本新聞 / 北九州市',
     '堺町・京町歓楽街 暴排運動 連載', None, '2015-2024'),
    ('mc_pachinko_industry', 'news', '日本遊技産業協同組合 / 業界紙',
     'パチンコ業界の暴排取り組み報道', None, '2010-2024'),
    ('mc_construction_industry', 'news', '建設業界紙',
     '建設業界の暴排取り組み — 工藤會事案を受けた業界対応', None, '2010-2024'),
    ('mc_pamphlet_local', 'ngo', '北九州市暴追運動推進会議',
     '地域住民向け暴排パンフレット・年次報告', None, '2010-2024'),
    ('mc_bar_owners', 'news', '西日本新聞',
     '小倉北区 飲食店経営者の暴排証言シリーズ', None, '2014-2020'),
    ('mc_kosakuin_witness', 'ruling', '福岡地裁',
     '工藤會公判 証人尋問記録', 'https://www.courts.go.jp/', '2015-2021'),
]


# site_slug, source_key, kind, date, title, summary, victim, weapon, resolution,
#   era_tag, faction_tag, severity
EVENTS = [
    # ===== 構造的記述 — 北九州三大組構図 =====
    ('yawata_iron_works_area', 'mc_yawata_kokura_moji',
     'lore', '1950s-1980s',
     '北九州の三大組構図(八幡・小倉・門司)',
     '戦後北九州の組織犯罪は「八幡(製鉄)・小倉(歓楽街)・門司(港)」の '
     '三大組構図として報道書籍に描かれた。'
     '工藤會は小倉軸を統合する組織として後に頂点に立つ。',
     None, None, None, '戦後闇市', '工藤組系', 3),

    # ===== 1990s 各種 =====
    ('kudokai_hq_kandake', 'mc_kobetsu_ji',
     'lore', '1992-1995',
     '指定暴力団 工藤連合草野一家としての時代',
     '1992年の暴対法施行から2000年の工藤會改称まで、'
     '組織名は「工藤連合草野一家」のまま指定暴力団として運用された。'
     '神岳本部はこの時期に既に「金看板」を掲げていた。',
     None, None, None, '高度成長', '工藤會', 3),

    ('moji_kanmon_line', 'mc_kobetsu_ji',
     'lore', '1990s',
     '関門海峡の組系列の往来',
     '1990年代の関門海峡は、九州側ヤクザと本州側ヤクザの往来監視ライン。'
     '門司港の海岸沿いに小さな組事務所が点在し、北九州市の現代史の '
     'もう一つの層を形成していた、と地元紙連載は伝える。',
     None, None, None, '高度成長', '工藤組系', 2),

    # ===== 2000s 各種 =====
    ('kudokai_hq_kandake', 'mc_kobetsu_ji',
     'lore', '2000-2005',
     '工藤會改称後の組織形態整流',
     '2000年の工藤會改称後、傘下団体の整理と会長制移行が進んだ。'
     '田中組・極東組・吉竹組などが主要傘下として再配置されたと '
     '報道書籍は整理する。',
     None, None, None, '平成抗争', '工藤會', 3),

    ('sakaimachi_quarter', 'mc_bar_owners',
     'lore', '2003-2008',
     '飲食店経営者の証言 — 「断れなかった時代」',
     '堺町歓楽街の飲食店経営者の証言シリーズには、「みかじめ料を断れなかった時代」の '
     '具体的な月額・徴収頻度・断ったときの嫌がらせの種類が記録されている。',
     '飲食店経営者', '脅迫', '継続的被害', '平成抗争', '工藤會', 3),

    # ===== 2010s — 公判進行 =====
    ('kokura_district_court', 'mc_court_chukan',
     'ruling', '2015-2020',
     '工藤會公判 — 証人尋問の連続',
     '2015年から2020年にかけて、福岡地裁での工藤會関連公判では '
     '証人尋問の日程が長期化。被害者・元組員・捜査員など '
     '多数の証人尋問が行われた。',
     None, None, None, '頂上作戦', '司法側', 3),

    ('kokura_district_court', 'mc_kosakuin_witness',
     'ruling', '2018-2020',
     '元組員証言 — 「指示系統」立証の核',
     '元工藤會組員の法廷証言が、組織トップへの指示系統認定の重要証拠に。'
     '直接証拠が乏しい中、組内の指示伝達様式・盃事の儀式的拘束を '
     '元組員が法廷で語った。',
     '組関係者', None, '判決根拠', '頂上作戦', '司法側', 4),

    ('kudokai_hq_kandake', 'mc_npa_2015',
     'lore', '2015',
     '警察白書 — 頂上作戦の意義評価',
     '平成27年(2015)版 警察白書は、前年の頂上作戦を '
     '「市民を直接標的にする組織トップへの首謀者責任追及」として '
     '異例の評価を与えた。',
     None, None, None, '頂上作戦', '司法側', 2),

    # ===== 個別傘下組 =====
    ('tanaka_gumi_offshoot', 'mc_kobetsu_ji',
     'faction_split', '2015-2017',
     '田中組 — 撤去ラッシュ初期',
     '頂上作戦直後、田中組系列の組事務所撤去が小倉北区・小倉南区で連続。'
     '報道写真には「組事務所跡」の更地化が並んだ。'
     '組員離脱者向けの相談窓口が暴追センターで急増した時期と重なる。',
     None, None, None, '頂上作戦', '田中組系', 3),

    ('kokuraminami_district', 'mc_kobetsu_ji',
     'faction_split', '2015-2019',
     '極東組・吉竹組 — 主要傘下の解散届',
     '工藤會主要傘下の極東組・吉竹組などが頂上作戦以降に解散届を提出、'
     'もしくは事務所撤去を進めた。'
     '報道では「傘下組撤去の波」として整理される。',
     None, None, None, '頂上作戦', '工藤會', 3),

    # ===== 関連企業 =====
    ('kudokai_hq_kandake', 'mc_kominzu_company',
     'lore', '2014-2020',
     '関連企業・フロント企業の整理',
     '頂上作戦以降、工藤會関連と疑われた企業への暴排勧告が継続的に行われた。'
     '警察庁・福岡県警の公表事案リストに、建設・解体・スクラップ・廃棄物処理など '
     '複数業種の企業が現れた。',
     None, None, None, '頂上作戦', '工藤會', 3),

    ('construction_extortion_kitakyushu', 'mc_construction_industry',
     'lore', '2010-2024',
     '建設業界の暴排対応の段階的進展',
     '建設業界は工藤會事案を受けて段階的に暴排対応を強化。'
     '元請け・下請けの契約書に暴排条項が標準化、関連業者リストの精査が進んだ。',
     None, None, None, '頂上作戦', '市民側', 2),

    ('pachinko_extortion_zone', 'mc_pachinko_industry',
     'lore', '2010-2024',
     'パチンコ業界の暴排取り組み',
     'パチンコ業界も同様に、組合主導の暴排講習・問題店舗の業界除名などを進めた。'
     '工藤會傘下からの威迫減少と並行して、業界内の自浄プロセスが整備された。',
     None, None, None, '頂上作戦', '市民側', 2),

    # ===== 解体当日 =====
    ('kudokai_hq_kandake_signboard', 'mc_koban_demolition',
     'demolition', '2019-07-04',
     '本部解体 — 着工日のルポ',
     '2019年7月4日、神岳1丁目の工藤會本部解体が着工。'
     '報道陣が現場周辺に並ぶ中、まず正面看板(金看板)がクレーンで吊り下げられた。'
     '夕方までに本部建物の上層が撤去された。',
     None, None, None, '頂上作戦', '工藤會', 4),

    ('kudokai_hq_kandake', 'mc_koban_demolition',
     'demolition', '2019-08-01',
     '本部 更地化完了',
     '2019年8月初旬、神岳1丁目の工藤會本部は完全に更地化された。'
     '解体に要した日数は約4週間。跡地は競売・売却プロセスに入った。',
     None, None, None, '頂上作戦', '工藤會', 4),

    # ===== 解体後 =====
    ('kudokai_hq_kandake', 'mc_atochi_problem',
     'lore', '2019-2024',
     '跡地問題 — 「再び組関係者に渡らないか」',
     '神岳1丁目の本部跡地の競売・売却過程で、「再び組関係者に渡らないか」という '
     '懸念が地元住民から提起された。北九州市議会でも議題となり、'
     '地権の移転過程の透明性確保が求められた。',
     None, None, None, '解体後', '市民側', 3),

    ('kudokai_hq_kandake', 'mc_kokurakita_satellite',
     'lore', '2019-2022',
     '組事務所跡 写真連載',
     '西日本新聞は、小倉北区の旧組事務所跡を巡る写真連載を継続。'
     '更地化・看板撤去・店舗転用などの絵を時系列で記録した。',
     None, None, None, '解体後', '工藤會', 2),

    # ===== コロナ禍 =====
    ('sakaimachi_quarter', 'mc_corona_bouhai',
     'lore', '2020-2022',
     'コロナ禍と暴排運動の継続',
     'コロナ禍で歓楽街は壊滅的打撃を受けたが、福岡県暴追運動推進センターは '
     '相談業務を継続。事業者の経営悪化に乗じた新たな威迫事案への対応が課題に。',
     None, None, None, '解体後', '市民側', 3),

    # ===== 元組員カルチャー =====
    ('kudokai_hq_kandake', 'mc_youtube_culture',
     'lore', '2018-2024',
     '元組員 YouTube カルチャーの隆盛',
     '懲役太郎・沖田臥竜ほか元組員系 YouTube チャンネルが2018年頃から本格化。'
     '指定暴力団生活の内側を本人視点で語る新メディア層が生まれ、'
     '工藤會を含む特定危険指定の世界観が若年層にも広がった(取扱注意・検証要)。',
     None, None, None, '解体後', '工藤會', 3),

    ('kudokai_hq_kandake', 'mc_ribetai_book',
     'lore', '2018-',
     '離脱手記の出版相次ぐ',
     '工藤會傘下の元組員による離脱手記が複数出版された。'
     '頂上作戦以降の組内の動揺、事務所撤去日の風景、'
     '若手組員の脱退選択などが具体的に描かれている。',
     None, None, None, '解体後', '田中組系', 3),

    # ===== 警察白書年次推移(イベント化) =====
    ('kudokai_hq_kandake', 'mc_npa_2020',
     'lore', '2020',
     '警察白書(2020)— 構成員数の大幅減確認',
     '令和2年版 警察白書は、工藤會の構成員数が頂上作戦から6年で約6割減と分析。'
     '事務所撤去・解散届の累積と並行する組織形態の弱体化を確認した。',
     None, None, None, '解体後', '司法側', 2),

    ('kudokai_hq_kandake', 'mc_npa_2023',
     'lore', '2023',
     '警察白書(2023)— 規制対象の地位維持',
     '令和5年版 警察白書は、工藤會の構成員数の減少が継続する一方、'
     '「特定危険指定」としての規制対象の地位は維持されると整理。'
     '解体後も組織形態のリスクが残存する評価。',
     None, None, None, '解体後', '司法側', 2),

    ('kudokai_hq_kandake', 'mc_npa_2024',
     'lore', '2024',
     '警察白書(2024)— 10年総括',
     '令和6年版 警察白書は、頂上作戦から10年の総括を含む。'
     '工藤會の構成員減少は継続、市民威迫事案も大幅減少と評価。'
     '一方で、潜在的離脱者の社会復帰支援は引き続き課題と整理。',
     None, None, None, '解体後', '司法側', 3),

    # ===== 上告審 =====
    ('kokura_district_court', 'mc_court_supreme',
     'ruling', '2024-2026',
     '最高裁 上告審 進行',
     '福岡高裁の控訴審判決(2024-03-12)を受け、検察側・被告側双方が上告。'
     '最高裁での上告審が進行中。指定暴力団トップへの死刑判決の評価をめぐる '
     '最終的な司法判断として注目される。',
     None, None, None, '解体後', '司法側', 4),

    # ===== 地域住民 =====
    ('ogura_keisatsu', 'mc_pamphlet_local',
     'lore', '2010-2024',
     '北九州市暴追運動推進会議の地域連携',
     '北九州市暴追運動推進会議は、地域自治会・商店街・小学校 PTA など '
     '複数階層と連携した暴排啓発を継続。神岳本部解体は「街の側が取り戻した」 '
     '象徴として地域パンフレットに繰り返し記載された。',
     None, None, None, '頂上作戦', '市民側', 2),

    # ===== 県警組対課 =====
    ('fukuoka_kenkei', 'mc_kokura_keisatsu_serial',
     'lore', '2015-',
     '福岡県警組対課 — 連載ノンフィクション',
     '西日本新聞は福岡県警組織犯罪対策課の日常を扱うノンフィクション連載を継続。'
     '頂上作戦の捜査手法・組員脱退者支援・市民威迫事案への対応 など、'
     '県警側の見えにくい仕事の記録として参照される。',
     None, None, None, '頂上作戦', '県警側', 3),
]


# ord, site_slug, year, title, body, spice, era_tag, faction_tag, source_key
LORE = [
    (500, 'yawata_iron_works_area', '1950s-1970s',
     '八幡・小倉・門司の地理的役割分担',
     '八幡(製鐵所労働者街)・小倉(中心市街・歓楽街)・門司(港湾)は、'
     '戦後北九州の経済構造とヤクザ文化双方の役割分担を担った。'
     '工藤組系は中津・門司、草野一家系は小倉、八幡系は地場小組織 — '
     'という分布が報道書籍に繰り返し描かれる。',
     3, '戦後闇市', '工藤組系', 'mc_yawata_kokura_moji'),

    (510, 'kokuraminami_district', '2000s-2014',
     '小倉北 vs 小倉南 — 本部と傘下の役割',
     '工藤會本部のあった小倉北区に対し、小倉南区には傘下組の事務所群が広く分布。'
     'この「北の頂点・南の足腰」の二層構造は、頂上作戦以降の撤去ラッシュで '
     '構造ごと崩れていった。',
     3, '平成抗争', '田中組系', 'mc_kobetsu_ji'),

    (520, 'kudokai_hq_kandake', '2014-2019',
     '本部「金看板」を見上げる風景',
     '2014年の頂上作戦から2019年の解体までの5年間、'
     '神岳本部は「会長拘束下・看板だけ残る」奇妙な状態だった。'
     '小倉北警察署の窓から見える距離に「金看板」が掲げ続けられていた事実は、'
     '戦後北九州の地理構造を最も濃く象徴する絵として地元紙が幾度も取り上げた。',
     5, '頂上作戦', '工藤會', 'mc_kobetsu_ji'),

    (530, 'kokura_district_court', '2018-2021',
     '公判の傍聴券抽選 — 列が並ぶ午前6時',
     '工藤會関連公判の日、福岡地裁小倉支部前には傍聴券抽選のために '
     '午前6時から並ぶ人の列ができた。地方裁判所支部としては異例の光景。'
     '報道陣・暴追関係者・一般市民・元組関係者と思しき人物が混在した。',
     4, '頂上作戦', '司法側', 'mc_court_chukan'),

    (540, 'kudokai_hq_kandake_signboard', '2019-07-04',
     '「金看板」がクレーンで吊り上げられた瞬間',
     '2019年7月4日、神岳本部の正面看板がクレーンで吊り下げられた瞬間。'
     '全国の主要メディアがリアルタイムで配信し、SNS でも瞬く間に拡散。'
     '「指定暴力団の象徴撤去」のアイコン映像として、海外メディアも繰り返し使用した。',
     5, '頂上作戦', '工藤會', 'mc_koban_demolition'),

    (550, 'sakaimachi_quarter', '2010-2024',
     '暴排ステッカーの年代別普及',
     '堺町・京町の飲食店店頭の暴排ステッカーは、2010年代前半は珍しい絵だったが、'
     '頂上作戦以降に急速に普及。2020年代には「ない店の方が珍しい」状態に。'
     '一枚の小さな絵が、街の側が拒否する集団意思の可視化として機能した。',
     3, '頂上作戦', '市民側', 'mc_st_sticker'),

    (560, 'kokuraminami_district', '2019-2024',
     '更地と看板のなくなった四つ角',
     '小倉北区の街角を歩くと、「ここにかつて組事務所があった」と '
     '地元の高齢者が指差す四つ角に出会う。'
     '更地・コインパーキング・店舗転用 — 跡地の表情は様々だが、'
     '「看板のない四つ角」は戦後北九州の風景の一部だった。',
     3, '解体後', '市民側', 'mc_kokurakita_satellite'),

    (570, 'sakaimachi_quarter', '2020-2022',
     'コロナ禍の歓楽街と暴排相談',
     'コロナ禍で歓楽街全体が打撃を受ける中、'
     '事業者の経営悪化に乗じる新型の威迫事案(借入仲介・コロナ給付金関連)が '
     '相談として出てきたと福岡県暴追センターは記録している。',
     3, '解体後', '市民側', 'mc_corona_bouhai'),

    (580, 'kudokai_hq_kandake', '2014-2024',
     '元組員 YouTube と「リアルなヤクザ」',
     '元組員系 YouTube チャンネルは2018年頃から本格化。'
     '工藤會を直接扱うものは少ないが、特定危険指定暴力団の日常を語ることで、'
     '報道では伝わらない「内側からの空気」が若年層に届く新メディア層が生まれた。'
     '一方で発信内容の検証が困難という問題も継続して指摘されている。',
     3, '解体後', '工藤會', 'mc_youtube_culture'),

    (590, 'fukuoka_kenkei', '2014-',
     '組対課の捜査員 — 数年がかりの追跡',
     '福岡県警組織犯罪対策課の捜査員は、頂上作戦の数年前から証拠を地道に積み上げた。'
     '「直接証拠は出ない」前提で組織トップへの責任を立てる捜査は '
     '記者・元捜査員の手記でも繰り返し描かれた異例の取り組み。',
     4, '頂上作戦', '県警側', 'mc_kokura_keisatsu_serial'),

    (600, 'kokura_district_court', '2018-2020',
     '元組員証言の重み',
     '元工藤會組員が法廷で証言した「指示系統」「盃事の拘束」「組内序列」は、'
     '直接証拠が乏しい本件の判決理由形成において重要な役割を果たした、と '
     '法律時報の判例解説は整理する。',
     4, '頂上作戦', '司法側', 'mc_kosakuin_witness'),

    (610, 'kudokai_hq_kandake', '2024',
     '頂上作戦10年の総括 — 数字で見る',
     '頂上作戦から10年(2014→2024)で:'
     '工藤會構成員数 約6-7割減・関連事務所撤去 数十件・'
     '本部建物解体完了・市民威迫事案大幅減 — 数字で見ると国内のヤクザ規制の '
     '最も顕著な成功事例の一つとして警察庁が位置づけた。',
     4, '解体後', '司法側', 'mc_npa_2024'),

    (620, 'kokura_district_court', '2024-2026',
     '最高裁 上告審 — 「死刑のゆくえ」',
     '一審の死刑・控訴審の無期懲役のいずれが最終判断となるかは、'
     '日本の組織犯罪対策のシンボルケースとして法学界・社会から注視されている。'
     '判決の確定タイミング自体が、戦後ヤクザ史の一つの区切りになる。',
     5, '解体後', '司法側', 'mc_court_supreme'),
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
    print(f'phase15_micro: +{ev_inserted} events, +{lr_inserted} lore')
    if missing:
        print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
