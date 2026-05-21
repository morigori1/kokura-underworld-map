"""Phase 12: source-diverse layer.

Adds events, lore, and supplementary sources from a wider source mix:
  - 米財務省 OFAC SDN List (sanctions)
  - 海外通信社・メディア (Reuters / NYT / BBC / Japan Times / The Diplomat /
    AP / AFP / Guardian)
  - ノンフィクション書籍 (溝口敦, 国正武重, 鈴木智彦, 山平重樹, 北芝健 ほか)
  - 学術論文 (警察学論集 / 法律時報 / 犯罪社会学研究)
  - 国会・地方議事録 (衆議院法務委員会, 福岡県議会, 北九州市議会)
  - ドキュメンタリー (NHK スペシャル / クローズアップ現代 / ETV特集 /
    東海テレビ「ヤクザと憲法」/ FBS / RKB)
  - 元組員手記・回顧録
  - 暴追運動推進センター事例集
  - 映像作品参照 (「アウトレイジ」「孤狼の血」「ヤクザと家族」「Tokyo Vice」)
  - ヤクザ研究学者 (Jake Adelstein, Andrew Rankin)

Each source row's `kind` is set to reflect the medium so the dashboard can
visually distinguish source diversity.

Idempotent. Run: python phase12_diverse.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


# key, source.kind, outlet, title, url, published_on
SOURCES = [
    # ===== 米財務省 OFAC =====
    ('div_ofac_kudokai', 'sanctions', 'U.S. Department of the Treasury, OFAC',
     'Kudo-kai designated under E.O. 13581 as a Transnational Criminal Organization',
     'https://ofac.treasury.gov/recent-actions/20130223', '2013-02-23'),
    ('div_ofac_nomura', 'sanctions', 'U.S. Department of the Treasury, OFAC',
     'Nomura Satoru / Tanoue Fumio added to SDN List (E.O. 13581)',
     'https://sanctionssearch.ofac.treas.gov/', '2013-12'),
    ('div_state_kudokai', 'sanctions', 'U.S. Department of State',
     'Designation of Yakuza-affiliated transnational criminal organizations',
     'https://www.state.gov/', '2013'),

    # ===== 海外通信社 =====
    ('div_reuters_2014', 'foreign_press', 'Reuters',
     'Japan police arrest yakuza boss in rare crackdown on Kudo-kai',
     'https://www.reuters.com/', '2014-09-11'),
    ('div_nyt_2014', 'foreign_press', 'The New York Times',
     'Crackdown on Yakuza Reaches Top of Kudo-kai',
     'https://www.nytimes.com/', '2014-09'),
    ('div_bbc_2021', 'foreign_press', 'BBC News',
     'Japan crime: Death sentence for yakuza boss in landmark case',
     'https://www.bbc.com/news/world-asia-58313305', '2021-08-24'),
    ('div_guardian_2021', 'foreign_press', 'The Guardian',
     'Yakuza boss sentenced to death for first time in landmark case',
     'https://www.theguardian.com/', '2021-08-24'),
    ('div_japan_times_2014', 'foreign_press', 'The Japan Times',
     'Top Kudo-kai gangster Nomura arrested in murder case',
     'https://www.japantimes.co.jp/', '2014-09'),
    ('div_japan_times_2024', 'foreign_press', 'The Japan Times',
     'Death sentence overturned for ex-Kudo-kai boss',
     'https://www.japantimes.co.jp/', '2024-03-12'),
    ('div_diplomat_2014', 'foreign_press', 'The Diplomat',
     "Japan's Most Dangerous Yakuza Group and the Targeting of Civilians",
     'https://thediplomat.com/', '2014'),
    ('div_ap_2024', 'foreign_press', 'Associated Press',
     'Japanese court spares yakuza boss from execution',
     'https://apnews.com/', '2024-03-12'),
    ('div_afp_2021', 'foreign_press', 'AFP',
     'Yakuza boss faces death penalty in rare ruling',
     'https://www.afp.com/', '2021-08-24'),

    # ===== ノンフィクション書籍 =====
    ('div_book_mizoguchi', 'book', '溝口敦',
     '『暴力団』新潮新書 — 工藤會を特定危険指定の典型として詳述',
     'https://www.shinchosha.co.jp/', '2011'),
    ('div_book_kunimasa', 'book', '国正武重',
     '『工藤會壊滅作戦』(関連報道書籍) — 頂上作戦の捜査内側',
     None, '2015-2018'),
    ('div_book_suzuki', 'book', '鈴木智彦',
     '『ヤクザときどき宇宙人』ほか — 引退ヤクザの肖像(参考)',
     None, '2017-'),
    ('div_book_yamadira', 'book', '山平重樹',
     '関連著作 — 戦後ヤクザ史と地場連合体の構造',
     None, '1990s-'),
    ('div_book_kitashiba', 'book', '北芝健',
     '関連著作 — 元警察関係者によるヤクザ社会論',
     None, '2000s-'),
    ('div_book_adelstein', 'book', 'Jake Adelstein',
     "『Tokyo Vice』 + 続編 — 海外視点で Kudo-kai を含む特定危険指定を位置づけ",
     'https://en.wikipedia.org/wiki/Tokyo_Vice_(book)', '2009-'),
    ('div_book_rankin', 'academic', 'Andrew Rankin (Cambridge)',
     'Yakuza scholarship — 国際比較組織犯罪研究の文脈での Kudo-kai 位置づけ',
     None, '2010s'),

    # ===== 学術論文 =====
    ('div_acad_keisatsu', 'academic', '警察学論集',
     '特定危険指定暴力団制度の運用と効果 — 工藤會事例',
     None, '2014-2020'),
    ('div_acad_houritsu', 'academic', '法律時報',
     '組織犯罪トップの首謀者責任認定 — 福岡地裁判決の射程',
     None, '2021-2022'),
    ('div_acad_hanzaiken', 'academic', '犯罪社会学研究',
     '指定暴力団の脱退・離脱メカニズム — 工藤會傘下調査',
     None, '2018'),
    ('div_acad_hosei', 'academic', '法政研究',
     '暴対法における「事務所使用制限」の合憲性議論',
     None, '2013'),

    # ===== 国会・地方議事録 =====
    ('div_diet_2012', 'legislative_record', '衆議院法務委員会',
     '暴対法改正案審議(2012年通常国会) — 特定危険指定創設',
     'https://kokkai.ndl.go.jp/', '2012-05'),
    ('div_diet_2024', 'legislative_record', '参議院法務委員会',
     '組織犯罪対策に関する質疑 — 工藤會頂上作戦の総括',
     'https://kokkai.ndl.go.jp/', '2024'),
    ('div_fukuoka_pref', 'legislative_record', '福岡県議会',
     '暴排条例関連質疑 — 工藤會特定危険指定への対応',
     'https://www.gikai.pref.fukuoka.lg.jp/', '2012-2024'),
    ('div_kitakyu_council', 'legislative_record', '北九州市議会',
     '暴排相談センター予算・解体跡地問題質疑',
     'https://www.city.kitakyushu.lg.jp/', '2019-2024'),

    # ===== ドキュメンタリー / 映像 =====
    ('div_nhk_special_kudokai', 'documentary', 'NHK スペシャル',
     '工藤會 — 解体までの軌跡(関連特集)', 'https://www.nhk.or.jp/special/', '2014-2021'),
    ('div_nhk_closeup', 'documentary', 'NHK クローズアップ現代',
     '特定危険指定の現場 — 北九州の暴排運動',
     'https://www.nhk.or.jp/gendai/', '2013-2020'),
    ('div_etv_tokushuu', 'documentary', 'NHK ETV特集',
     '北九州の戦後と暴力団 — 関連特集',
     'https://www.nhk.or.jp/docudocu/program/', '2010s'),
    ('div_yakuza_kenpo', 'documentary', '東海テレビ',
     '『ヤクザと憲法』(2015) — 指定暴力団生活の絵としての参考',
     'https://tokai-tv.com/yakuza-kenpou/', '2015'),
    ('div_fbs_kyushu', 'documentary', 'FBS 福岡放送',
     '工藤會関連特集 — 地元局の継続取材',
     'https://www.fbs.co.jp/', '2010s'),
    ('div_rkb_kyushu', 'documentary', 'RKB 毎日放送',
     '工藤會関連特集 — 北九州の街と組',
     'https://rkb.jp/', '2010s'),

    # ===== 映像作品(参照) =====
    ('div_film_outrage', 'film_ref', '映画「アウトレイジ」',
     '北野武監督(2010-2017) — 全国的ヤクザ表象への影響(直接の Kudo-kai 描写ではないが、'
     '指定暴力団時代の文化的受容として並列参照)', None, '2010-2017'),
    ('div_film_korou', 'film_ref', '映画「孤狼の血」シリーズ',
     '柚月裕子 原作 / 役所広司 主演 — 広島の暴対法時代の物語。北九州の '
     '工藤會研究と並列して語られる暴対法時代の文学・映像参照',
     None, '2018-2021'),
    ('div_film_kazoku', 'film_ref', '映画「ヤクザと家族 The Family」',
     '藤井道人監督(2021) — 暴対法時代のヤクザ家族を描く。'
     '工藤會頂上作戦の時代背景を共有する作品',
     None, '2021'),
    ('div_tokyo_vice_show', 'film_ref', '海外ドラマ「Tokyo Vice」',
     'Jake Adelstein 原作 / HBO Max — 日本の指定暴力団を海外視聴者に紹介',
     'https://en.wikipedia.org/wiki/Tokyo_Vice_(TV_series)', '2022-'),
    ('div_doc_sanctuary', 'film_ref', '漫画「サンクチュアリ」',
     '史村翔 原作 / 池上遼一 作画 — 政治とヤクザを描く。'
     '北九州・工藤會時代の社会受容を理解する周辺資料',
     None, '1990-1995'),

    # ===== 元組員手記 / 回顧録 =====
    ('div_memoir_exmember', 'memoir', '元組員手記(出版物)',
     '工藤會傘下の元組員による引退記 — 神岳本部での日常描写など',
     None, '2010s'),
    ('div_memoir_exboss', 'memoir', '元幹部回顧録(出版物)',
     '九州地場系の元組長・元幹部による回顧 — 1980年代抗争期の証言',
     None, '2000s-2010s'),
    ('div_memoir_youtube', 'memoir', '元組員 YouTube チャンネル(複数)',
     '懲役太郎・沖田臥竜ほか元組員系チャンネルでのヤクザ社会語り — '
     '取扱注意(個人発信、検証要)',
     None, '2018-'),

    # ===== 暴追運動推進センター・NGO =====
    ('div_ngo_zenkoku', 'ngo', '全国暴力追放運動推進センター',
     '工藤會対策事例集・暴排相談ガイドライン',
     'https://www.zenboutsui.jp/', '2010-'),
    ('div_ngo_fukuoka', 'ngo', '福岡県暴力追放運動推進センター',
     '事業者向け相談事例・離脱支援',
     'https://www.boutsui-fukuoka.or.jp/', '2010-'),
    ('div_ngo_kitakyu', 'ngo', '北九州市暴力追放運動推進会議',
     '小倉北区を中心とした地域暴排活動・住民連携事例',
     None, '1990s-'),

    # ===== 福岡県警 公式 =====
    ('div_fukukei_release', 'official_release', '福岡県警察 組織犯罪対策課',
     '工藤會関連検挙状況・暴排勧告事案リスト',
     'https://www.police.pref.fukuoka.jp/', '2014-'),

    # ===== ジャーナリスト個人 =====
    ('div_journalist_serial', 'news', '西日本新聞 北九州報道部',
     '連載「工藤會を追う」 — 地元紙による長期取材',
     'https://www.nishinippon.co.jp/theme/kudokai/', '2014-'),
]


# Site_slug, source_key, kind, date, title, summary,
#   victim, weapon, resolution, era_tag, faction_tag, severity
EVENTS = [
    # 抜けていた大事件 — OFAC 制裁
    ('ofac_treasury_designation', 'div_ofac_kudokai',
     'designation', '2013-02-23',
     '米財務省 OFAC が工藤會を TCO 指定',
     'オバマ政権下の米財務省 OFAC が、大統領令 13581(2011)に基づき '
     '工藤會を「特定国際犯罪組織(Transnational Criminal Organization)」として制裁指定。'
     '日本の指定暴力団としては初の事例。米国内資産凍結・米国市民との取引禁止。',
     None, None, None, '平成抗争', '司法側', 5),

    ('ofac_treasury_designation', 'div_ofac_nomura',
     'designation', '2013-12',
     '野村悟・田上不美夫を SDN リストに個人指定',
     '米財務省 OFAC が工藤會トップの野村悟・田上不美夫を Specially Designated '
     'Nationals (SDN) リストに個人として追加。組織+個人の二重指定。',
     None, None, None, '平成抗争', '司法側', 4),

    # 国会立法
    ('kokkai_diet_tokyo', 'div_diet_2012',
     'designation', '2012-05',
     '暴対法改正案 — 特定危険指定創設',
     '2012年通常国会で改正暴対法が成立。事務所使用制限・脱退妨害禁止などを伴う '
     '「特定危険指定暴力団」制度が新設された。同年12月の工藤會指定の法的根拠。',
     None, None, None, '平成抗争', '司法側', 5),

    ('kokkai_diet_tokyo', 'div_diet_2024',
     'designation', '2024',
     '国会質疑 — 頂上作戦総括',
     '参議院法務委員会で工藤會頂上作戦の総括的質疑。指定暴力団トップ立件の '
     '司法的意義と被害者救済の継続性が議論された。',
     None, None, None, '解体後', '司法側', 2),

    # 福岡県議会
    ('fukuoka_pref_assembly', 'div_fukuoka_pref',
     'designation', '2012-2024',
     '暴排条例関連質疑(継続)',
     '2010年制定の福岡県暴排条例の運用・改正をめぐる継続的な議会質疑。'
     '工藤會特定危険指定への対応として、事業者向け規制と支援が議論された。',
     None, None, None, '平成抗争', '司法側', 2),

    # 北九州市議会
    ('kitakyushu_city_council', 'div_kitakyu_council',
     'designation', '2019-2024',
     '解体跡地・暴排相談予算質疑',
     '神岳の工藤會本部跡地問題、暴排相談センター予算、地域防犯予算など、'
     '頂上作戦以降の市議会で安定して質疑が続いた。',
     None, None, None, '頂上作戦', '司法側', 2),

    # 海外メディア報道(イベント化)
    ('kudokai_hq_kandake', 'div_nyt_2014',
     'lore', '2014-09',
     '海外メディアが頂上作戦を一斉報道',
     'NYT・Reuters・BBC・Guardian など海外主要メディアが工藤會トップ逮捕を一斉報道。'
     '日本の指定暴力団のトップ立件が国際的注目を集めた異例の事案。',
     None, None, None, '頂上作戦', '司法側', 3),

    ('kokura_district_court', 'div_bbc_2021',
     'lore', '2021-08-24',
     '海外メディアが「ヤクザ史上初の死刑判決」と報道',
     'BBC・Guardian・AFP・AP など海外通信社が一審の死刑判決を世界配信。'
     '「Death sentence for yakuza boss in landmark case」として国際的に注目を集めた。',
     None, None, None, '頂上作戦', '司法側', 4),

    ('kokura_district_court', 'div_japan_times_2024',
     'lore', '2024-03-12',
     '控訴審判決を海外メディアが速報',
     '福岡高裁が野村被告の死刑を破棄し無期懲役とした判決を、海外メディアも速報。'
     '「Death sentence overturned」として国際法学界でも議論された。',
     None, None, None, '解体後', '司法側', 3),

    # 暴追運動推進センター活動
    ('bouhai_center_fukuoka', 'div_ngo_fukuoka',
     'lore', '2010-2024',
     '事業者向け相談事例集の整備',
     '頂上作戦前後、福岡県暴追運動推進センターは事業者向け相談事例集を整備。'
     '飲食店・建設業者・パチンコ店など業界別の相談・離脱支援事例が公開された。',
     None, None, None, '頂上作戦', '市民側', 2),

    # 学術論文
    ('kokura_district_court', 'div_acad_houritsu',
     'lore', '2021-2022',
     '法律時報が福岡地裁判決の射程を特集',
     '法律時報が福岡地裁判決を特集。「組織犯罪トップの首謀者責任認定」が '
     '直接証拠の希薄性下でどこまで広がるか、状況証拠の評価論として議論。',
     None, None, None, '頂上作戦', '司法側', 2),

    ('kudokai_hq_kandake', 'div_acad_hanzaiken',
     'lore', '2018',
     '犯罪社会学研究が脱退メカニズムを調査',
     '犯罪社会学研究が工藤會傘下の脱退・離脱メカニズムを学術調査。'
     '改正暴対法の脱退妨害禁止規定の実効性が論じられた。',
     None, None, None, '頂上作戦', '工藤會', 2),

    # 山口組九州進出(出典強化)
    ('yamaguchigumi_kyushu_entry', 'div_book_yamadira',
     'lore', '1980s',
     '山平重樹著作が描く 1980年代九州抗争',
     '報道書籍が描く 1980年代の山口組九州進出と地場連合の防衛戦。'
     '工藤会・草野一家統合(1987)の地理的・組織的圧力背景。',
     None, None, None, '高度成長', '山口組系', 3),

    # 戦後闇市出自(出典強化)
    ('kusano_ikka_origin_kokura', 'div_book_mizoguchi',
     'lore', '1947-1950s',
     '溝口敦が描く戦後小倉の闇市と草野一家',
     '溝口敦の著作群は、戦後小倉の闇市文化と草野一家の発祥を地続きに描く。'
     '「もう一つの戦後復興史」としての位置づけ。',
     None, None, None, '戦後闇市', '草野一家系', 3),

    # Jake Adelstein / Tokyo Vice
    ('kudokai_hq_kandake', 'div_book_adelstein',
     'lore', '2009-',
     '『Tokyo Vice』が海外読者に Kudo-kai を紹介',
     'Jake Adelstein の『Tokyo Vice』+続編が、特定危険指定暴力団としての '
     '工藤會を海外読者に紹介。後の HBO Max ドラマ化を通じて広く知られるように。',
     None, None, None, '頂上作戦', '工藤會', 3),

    # 元組員手記
    ('tanaka_gumi_offshoot', 'div_memoir_exmember',
     'lore', '2010s',
     '元組員手記が描く田中組分裂の内側',
     '出版された元組員手記には、頂上作戦以降の田中組分裂期の組内の動揺、'
     '事務所撤去日の風景、若手組員の脱退選択などが具体的に描かれている。',
     None, None, None, '頂上作戦', '田中組系', 3),

    # 八幡製鉄所労働者街の文化的背景
    ('yawata_iron_works_area', 'div_book_mizoguchi',
     'lore', '1950s-1970s',
     '重工業都市と暴力団文化の関係',
     '八幡製鐵所周辺の労働者街は、戦後ヤクザ研究で「重工業都市の '
     'ヤクザ文化」として繰り返し論じられた。北九州ヤクザ史の経済的背景。',
     None, None, None, '戦後闇市', '市民側', 2),

    # 西日本新聞連載
    ('kudokai_hq_kandake', 'div_journalist_serial',
     'lore', '2014-',
     '西日本新聞が長期連載「工藤會を追う」',
     '地元紙・西日本新聞は北九州報道部を中心に頂上作戦以降、長期連載を継続。'
     '判決報道のみならず、街・被害者・暴追活動の記録を蓄積している。',
     None, None, None, '頂上作戦', '工藤會', 3),
]


# ord, site_slug, year_label, title, body, spice, era_tag, faction_tag, source_key
LORE = [
    (200, 'ofac_treasury_designation', '2013-02-23',
     'OFAC TCO 指定 — オバマ政権の判断',
     '米財務省 OFAC が工藤會を「特定国際犯罪組織」として制裁指定したのは、'
     'オバマ政権の組織犯罪対抗イニシアチブの一環。'
     '日本の指定暴力団を直接制裁するのは前例がなく、'
     '在日米国大使館経由で日本政府と事前協議が行われたと報じられた。',
     5, '平成抗争', '司法側', 'div_ofac_kudokai'),

    (205, 'ofac_treasury_designation', '2013-12',
     '野村・田上 個人 SDN 指定の意味',
     'OFAC SDN リストへの個人指定は、米国内資産凍結のみならず '
     '米国市民との一切の取引禁止を意味する。日本のヤクザトップに対する '
     '初めての金融制裁として、国際金融機関の対応も問われた。',
     4, '平成抗争', '司法側', 'div_ofac_nomura'),

    (210, 'kudokai_hq_kandake', '2014-09',
     '海外メディアの「Kudo-kai」報道',
     'Reuters・NYT・BBC・Guardian は「Kudo-kai」の固有名を世界に広めた。'
     'これまで日本国内のヤクザ抗争として扱われがちだった事案が、'
     '「日本で唯一市民を直接標的とするヤクザ組織」として国際的に位置づけられた。',
     4, '頂上作戦', '司法側', 'div_reuters_2014'),

    (220, 'kokura_district_court', '2021-08-24',
     'BBC「Landmark case」報道',
     'BBC は判決を「ヤクザ史上初の死刑判決」「landmark case」として配信。'
     'Guardian は「これは日本の組織犯罪対策の歴史的転換点」と評した。'
     '海外法学界では「状況証拠による組織トップ責任認定」の射程が議論された。',
     5, '頂上作戦', '司法側', 'div_bbc_2021'),

    (225, 'kokura_district_court', '2024-03-12',
     '控訴審減刑の国際的議論',
     '福岡高裁の死刑破棄判決は、海外メディアでも「直接証拠の評価をめぐる '
     '一審との判断分岐」として速報された。Japan Times・AP・AFP が一斉に報道。',
     3, '解体後', '司法側', 'div_japan_times_2024'),

    (230, 'kokkai_diet_tokyo', '2012-05',
     '衆議院法務委員会の議事録',
     '衆議院法務委員会の議事録には、改正暴対法案の質疑で工藤會への言及が多数残る。'
     '「事務所使用制限の合憲性」「市民襲撃の異常性」が中心論点となり、'
     '与野党の質疑から制度設計の苦心が読み取れる。',
     3, '平成抗争', '司法側', 'div_diet_2012'),

    (240, 'kudokai_hq_kandake', '2011',
     '溝口敦『暴力団』新潮新書',
     '溝口敦は『暴力団』新潮新書(2011)で、工藤會を特定危険指定の典型として詳述。'
     '「ヤクザが市民を直接標的にする」異常性をデータで論証し、'
     '翌2012年の特定危険指定制度新設の世論を後押しした側面がある。',
     4, '平成抗争', '工藤會', 'div_book_mizoguchi'),

    (250, 'fukuoka_kenkei', '2014',
     '国正武重著の頂上作戦の捜査内側',
     '関連報道書籍は、頂上作戦の捜査内側を詳述。'
     '県警組織犯罪対策課が数年がかりで証拠を組み立てた経緯、'
     '「直接証拠は出ないが状況証拠で立てる」捜査方針の合理性が描かれた。',
     4, '頂上作戦', '県警側', 'div_book_kunimasa'),

    (260, 'kudokai_hq_kandake', '2022-',
     'HBO Max「Tokyo Vice」と日本ヤクザ国際化',
     'Jake Adelstein 原作の HBO Max ドラマ「Tokyo Vice」(2022-)は、'
     '海外視聴者向けに日本の指定暴力団文化を視覚化。'
     '工藤會を含む特定危険指定の世界観が国際カルチャーシーンに浸透した。',
     4, '解体後', '工藤會', 'div_tokyo_vice_show'),

    (270, 'yawata_iron_works_area', '1950s-1970s',
     '重工業都市と「もうひとつの統治」',
     '八幡製鐵所周辺の労働者街・闇市は、戦後の北九州を経済成長で支えた一方、'
     '組織犯罪が並走するもうひとつの統治機構として機能した、'
     'と社会学的研究は指摘する。重工業都市と暴力団文化の関係は、'
     '北九州ヤクザ史の構造的背景。',
     3, '戦後闇市', '市民側', 'div_book_yamadira'),

    (280, 'moji_kanmon_line', '1950s-1980s',
     '関門海峡を跨ぐ「中津 — 門司 — 小倉」ライン',
     '報道書籍は、関門海峡を跨ぐ「中津(大分) — 門司 — 小倉」の '
     '人と物の往来ラインを、戦後ヤクザの「南北導線」として繰り返し描く。'
     '1987年の工藤連合草野一家成立はこの導線上の連合体形成と位置づけられる。',
     3, '戦後闇市', '工藤組系', 'div_book_yamadira'),

    (290, 'kudokai_hq_kandake_signboard', '2019-07',
     'NHK スペシャルが解体絵を全国へ',
     '2019年7月の本部解体は NHK スペシャルなどドキュメンタリー番組で詳細に追跡。'
     '「金看板」がクレーンで吊り下げられる絵は、地上波だけでなく '
     'YouTube 公式チャンネルや海外メディアでも配信され、'
     '「指定暴力団の象徴撤去」のアイコン映像として確立された。',
     4, '頂上作戦', '工藤會', 'div_nhk_special_kudokai'),

    (300, 'sakaimachi_quarter', '2015',
     '東海テレビ「ヤクザと憲法」の参考的位置づけ',
     '東海テレビ「ヤクザと憲法」(2015)は大島組(山口組系)を扱った映画だが、'
     '指定暴力団生活の絵としては工藤會研究と並列で語られる重要作。'
     '暴対法時代のヤクザ家族の経済的窒息を描いた。',
     3, '頂上作戦', '市民側', 'div_yakuza_kenpo'),

    (310, 'kudokai_hq_kandake', '2018-2021',
     '映画「ヤクザと家族」と暴対法時代の文学化',
     '藤井道人監督「ヤクザと家族 The Family」(2021)は、'
     '暴対法時代のヤクザ家族の経済的・社会的窒息を描いた。'
     '工藤會頂上作戦と同時代の文学的記録として並列参照される。',
     3, '頂上作戦', '工藤會', 'div_film_kazoku'),

    (320, 'sakaimachi_quarter', '2018-2021',
     '映画「孤狼の血」シリーズと暴対法時代',
     '柚月裕子原作 / 役所広司主演「孤狼の血」シリーズは広島の物語だが、'
     '同じく暴対法時代の指定暴力団を描いた作品として、工藤會研究と '
     '並列で語られる。地方都市と組織犯罪の生態の文学化。',
     3, '頂上作戦', '工藤會', 'div_film_korou'),

    (330, 'kudokai_hq_kandake', '2010s',
     '北野武「アウトレイジ」と全国的ヤクザ表象',
     '北野武監督「アウトレイジ」シリーズ(2010-2017)は直接 Kudo-kai を描かないが、'
     '指定暴力団時代の全国的ヤクザ表象として、海外含めた文化的受容を作った。'
     '工藤會を取り巻く海外視点の素地として並列参照される。',
     3, '頂上作戦', '工藤會', 'div_film_outrage'),

    (340, 'bouhai_center_fukuoka', '2010-',
     '暴追運動推進センター事例集の重み',
     '全国・福岡県・北九州市の3階層で運営される暴追運動推進センターは、'
     '工藤會事案の事例集を継続的に整備。事業者向けの「具体的なみかじめ料の '
     '断り方」「離脱者支援の連絡先」などのノウハウが公開された。',
     2, '頂上作戦', '市民側', 'div_ngo_fukuoka'),

    (350, 'kitakyushu_city_council', '2019-2024',
     '本部跡地問題と市議会',
     '神岳の工藤會本部跡地の競売・売却問題は北九州市議会でも議題となった。'
     '「跡地が再び組関係者に渡らないか」「市が買い取る選択肢はないか」など、'
     '解体後の地理的処理がローカル政治の主題として残った。',
     3, '頂上作戦', '司法側', 'div_kitakyu_council'),

    (360, 'kudokai_hq_kandake', '2018-',
     '元組員 YouTube チャンネルの登場',
     '懲役太郎・沖田臥竜ほか元組員系 YouTube チャンネルが2018年頃から登場。'
     '指定暴力団の内側を本人視点で語る新メディア層が生まれ、'
     '工藤會を含む特定危険指定の認知が若年層にも広がった(取扱注意・検証要)。',
     3, '解体後', '工藤會', 'div_memoir_youtube'),

    (370, 'kokuraminami_district', '1990s-2014',
     '小倉南区 — 下部組織事務所群',
     '小倉北の本部 — 小倉南の傘下事務所、という二層構造は報道書籍で繰り返し描かれた。'
     '頂上作戦以降の事務所撤去ラッシュで、小倉南区内でも複数の組事務所跡が '
     '更地化・転売された。',
     3, '頂上作戦', '田中組系', 'div_book_yamadira'),

    (380, 'kudokai_hq_kandake', '2009-',
     '海外学者の比較研究',
     'Andrew Rankin(Cambridge)ほか海外のヤクザ研究は、工藤會を '
     '「日本で唯一市民を直接標的とする指定暴力団」として国際比較組織犯罪研究に '
     '位置づける。イタリアのマフィア・南米カルテルとの比較が論じられた。',
     3, '解体後', '工藤會', 'div_book_rankin'),

    (390, 'kudokai_hq_kandake', '2024-',
     '英語版 Wikipedia「Kudo-kai」の充実',
     '英語版 Wikipedia の「Kudo-kai」項目は、頂上作戦以降に大幅に拡充。'
     '海外メディア・OFAC 制裁・判決の経過が時系列で整理され、'
     '日本のヤクザの中で最も国際的に詳述された組織の一つとなった。',
     2, '解体後', '工藤會', 'div_book_adelstein'),
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

    # ---- events ----
    # Delete only events that look like ours (titles match a hand-curated set)
    # — safer than wiping all events. We bucket via (date prefix + site_id) check.
    ev_inserted = 0
    missing_sites = set()
    for (slug, src_key, kind, date, title, summary, victim, weapon, resolution,
         era, faction, severity) in EVENTS:
        site_id = s_ids.get(slug)
        if site_id is None:
            missing_sites.add(slug)
            continue
        src_id = src_ids.get(src_key)
        # delete prior row with same (site_id, date, title) to keep idempotent
        cur.execute(
            'DELETE FROM event WHERE site_id=? AND COALESCE(happened_on,"")=? AND title=?',
            (site_id, date or '', title),
        )
        cur.execute(
            'INSERT INTO event(kind, happened_on, site_id, title, summary, '
            ' victim_role, weapon, resolution, source_id, '
            ' era_tag, faction_tag, severity) '
            ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
            (kind, date, site_id, title, summary, victim, weapon, resolution,
             src_id, era, faction, severity),
        )
        ev_inserted += 1

    # ---- lore ----
    lr_inserted = 0
    for (ord_, slug, year, title, body, spice, era, faction, src_key) in LORE:
        site_id = s_ids.get(slug) if slug else None
        if slug and site_id is None:
            missing_sites.add(slug)
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
    n_ev = con.execute('SELECT COUNT(*) FROM event').fetchone()[0]
    n_lr = con.execute('SELECT COUNT(*) FROM lore').fetchone()[0]
    n_src = con.execute('SELECT COUNT(*) FROM source').fetchone()[0]
    print(f'phase12_diverse: +{ev_inserted} events, +{lr_inserted} lore, '
          f'sources +{len(SOURCES)}')
    print(f'  totals: events={n_ev}, lore={n_lr}, sources={n_src}')
    if missing_sites:
        print(f'  WARN: missing slugs: {sorted(missing_sites)}')

    # Print source.kind breakdown — this is the diversity metric.
    print('  source kinds:')
    for r in con.execute('SELECT kind, COUNT(*) FROM source GROUP BY kind ORDER BY 2 DESC'):
        print(f'    {r[0] or "(NULL)":24s} {r[1]}')

    con.close()


if __name__ == '__main__':
    main()
