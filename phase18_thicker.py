"""Phase 18: thickness — 戦前史・食文化・家族・メディア表象・全国/国際比較・金融。

このマップを単なる工藤會年表から、戦後北九州〜全国〜世界の組織犯罪コンテキスト
までを射程に入れた厚いオブジェクトに引き伸ばすための層。

カバー:
  1. 戦前史(1901-1945)— 八幡製鐵所開業、関東大震災移住、戦時下闇市萌芽、
     小倉空襲・原爆代替標的、終戦・闇市最盛期
  2. 食文化と街 — 資さんうどん、堺町ホルモン、屋台横丁、労働者街の食
  3. 家族・二世・女性 — 公開報道に基づく、ヤクザ家族の周辺カルチャー
  4. メディア表象 — 「クローズ」「Worst」(高橋ヒロシ・北九州)、北方謙三
     「ブラディ・ドール」(門司港)、「龍が如く」(SEGA)、演歌・実話誌
  5. 全国比較 — 24 指定暴力団のうち主要組織(山口組・住吉会・稲川会・会津小鉄会・
     極東会・浪川会・共政会・旭琉会)を並列表示
  6. 国際比較 — イタリア・コーザ・ノストラ / 'ンドランゲタ / 香港三合会 /
     米 La Cosa Nostra / メコン詐欺コンパウンド(SS プロジェクト相互参照)
  7. 金融 — 銀行業界の反社対応史(2007 反社チェック・2013 みずほ事件・暗号資産)

Idempotent. Run: python phase18_thicker.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    # ===== 戦前史 =====
    ('th_yawata_seitetsu_history', 'book', '北九州市史 / 日本製鉄社史',
     '八幡製鐵所 操業開始(1901)関連', None, '1901-'),
    ('th_kanto_dai_shinsai', 'book', '関東大震災 関連書籍',
     '1923 関東大震災と九州への人口流入', None, '1923-'),
    ('th_wartime_kokura', 'book', '北九州市史 / 福岡県史',
     '戦時下の小倉と闇取引萌芽', None, '1937-1945'),
    ('th_yawata_kushuu', 'book', '北九州市史 / 日本製鉄社史',
     '八幡空襲(1944-08-19 / 1945-06-25)', None, '1944-1945'),
    ('th_kokura_kushuu', 'book', '北九州市史',
     '小倉空襲(1945-08-08)・原爆代替標的(1945-08-09)', None, '1945-08'),
    ('th_postwar_yamiichi', 'book', '北九州市史 / 西日本新聞 戦後特集',
     '戦後闇市の形成(1945-09 〜)', None, '1945-1955'),
    ('th_chosen_sensou_tokuju', 'book', '日本経済史',
     '朝鮮戦争特需と北九州(1950-1953)', None, '1950-1953'),
    ('th_kitakyu_5shi_gappei', 'official_release', '北九州市',
     '5市合併・北九州市発足(1963-02-10)', 'https://www.city.kitakyushu.lg.jp/', '1963-02-10'),

    # ===== 食文化 =====
    ('th_sasashi_history', 'news', '西日本新聞 / 北九州市政だより',
     '資さんうどん 創業50周年関連報道', None, '2025'),
    ('th_horumon_culture', 'book', '北九州食文化研究',
     '労働者街と内臓食の系譜 — 関連書籍', None, '2000s-'),
    ('th_yatai_history', 'news', '西日本新聞 / RKB',
     '小倉駅前 屋台横丁 回顧連載', None, '2000s-2010s'),

    # ===== 家族・女性・二世 =====
    ('th_yakuza_family_book', 'book', '実話誌系出版 / 一般出版社',
     'ヤクザ家族の周辺カルチャー 関連書籍', None, '2000s-'),
    ('th_njourney_kazoku', 'documentary', 'NHK ETV特集 / その他',
     '指定暴力団家族の社会的孤立 ドキュメンタリー', None, '2010s'),
    ('th_2sei_school', 'news', '西日本新聞 連載',
     'ヤクザ二世の学校生活 — 公開された家族の物語', None, '2014-2019'),

    # ===== メディア・表象 =====
    ('th_crows_kitakyu_setting', 'book', '秋田書店',
     '高橋ヒロシ「クローズ」「Worst」関連報道', None, '1990-2014'),
    ('th_kitagata_bloody_doll', 'book', '集英社',
     '北方謙三「ブラディ・ドール」シリーズ', None, '1980s-1990s'),
    ('th_ryugagotoku_sega', 'film_ref', 'セガ',
     '「龍が如く」シリーズ', 'https://ryu-ga-gotoku.com/', '2005-'),
    ('th_yakuza_enka', 'book', '音楽雑誌・演歌史',
     '演歌・歌謡曲における任侠表象', None, '1960s-'),
    ('th_yakuza_manga_general', 'book', '漫画史研究',
     'ヤクザ漫画の系譜(劇画路線含む)', None, '1960s-'),
    ('th_jitsuwa_special', 'news', '月刊『創』 / 実話誌',
     '工藤會特集記事多数', None, '1990s-'),
    ('th_fabel_manga', 'book', '講談社',
     '南勝久「ザ・ファブル」 — 暴対法時代の引退ヤクザ漫画', None, '2014-'),
    ('th_outrage_kitano', 'film_ref', '松竹 / バンダイビジュアル',
     '北野武「アウトレイジ」シリーズ(2010-2017)', None, '2010-2017'),

    # ===== 全国比較 =====
    ('th_yamaguchigumi_history', 'book', '溝口敦 ほか',
     '六代目山口組 関連書籍', None, '2005-'),
    ('th_sumiyoshikai_history', 'book', '実話誌系 ほか',
     '住吉会 関連報道', None, '1990s-'),
    ('th_inagawakai_history', 'book', '実話誌系 ほか',
     '稲川会 関連報道', None, '1990s-'),
    ('th_aizukotetsu_history', 'book', '京都 ヤクザ史 関連',
     '会津小鉄会 関連報道', None, '1990s-'),
    ('th_kyokutokai_tekiya', 'book', '関東テキ屋系 関連書籍',
     '極東会 関連報道', None, '2000s-'),
    ('th_namikawakai_kyushu', 'news', '西日本新聞',
     '浪川会(旧九州誠道会)関連報道', None, '2013-'),
    ('th_kyokuseikai_hiroshima', 'book', '柚月裕子 ほか / 広島ヤクザ史',
     '共政会 関連 — 広島ヤクザ史', None, '1990s-'),
    ('th_kyokuryukai_okinawa', 'news', '沖縄タイムス / 琉球新報',
     '旭琉会 関連報道', None, '1990s-'),

    # ===== 国際比較 =====
    ('th_cosa_nostra_book', 'book', 'John Dickie ほか',
     'シチリア コーザ・ノストラ研究', None, '2000s-'),
    ('th_ndrangheta_book', 'book', 'Antonio Nicaso ほか',
     '\'ンドランゲタ 研究', None, '2010s-'),
    ('th_hk_triads', 'book', 'Yiu Kong Chu ほか',
     '香港 三合会 研究', None, '2000s-'),
    ('th_us_lcn_fbi', 'official_release', 'FBI',
     '米国 La Cosa Nostra(LCN)関連発表',
     'https://www.fbi.gov/investigate/organized-crime', '2000s-'),
    ('th_mekong_compounds', 'news', 'Reuters / OCCRP / 西日本新聞',
     'メコン地域 詐欺コンパウンド報道(SS プロジェクト参照)', None, '2018-'),
    ('th_rankin_comparative', 'academic', 'Andrew Rankin (Cambridge)',
     '日本ヤクザ vs マフィア — 比較組織犯罪研究', None, '2010s-'),

    # ===== 金融・反社対応 =====
    ('th_finance_2007', 'official_release', '政府指針',
     '反社会的勢力との関係遮断指針(2007)', None, '2007-06'),
    ('th_finance_2011', 'official_release', '政府指針',
     '企業による反社会的勢力排除の指針(2011)', None, '2011'),
    ('th_mizuho_2013', 'news', '朝日新聞 / 毎日新聞 / 日経新聞',
     'みずほ銀行 反社融資問題報道(2013-2014)', None, '2013-2014'),
    ('th_crypto_aml', 'official_release', '金融庁',
     '暗号資産取引所の反社・AML 対応強化(2018-)', None, '2018-'),
    ('th_zenginkyo_clause', 'ngo', '全国銀行協会',
     '反社条項の標準化と取引約款への組み込み', None, '2008-'),
]


# site_slug, source_key, kind, date, title, summary, victim, weapon, resolution,
#   era_tag, faction_tag, severity
EVENTS = [
    # ===== 戦前史 =====
    ('yawata_seitetsu_1901', 'th_yawata_seitetsu_history',
     'lore', '1901-11-18',
     '官営八幡製鐵所 操業開始',
     '明治34年(1901)11月18日、官営八幡製鐵所が操業開始。'
     '北九州が日本の重工業の中核地となり、労働者の大量流入が始まった。'
     '戦後の闇市・労働者街文化・ヤクザ系列の地理的分布の経済的根拠。',
     None, None, None, '戦後闇市', '市民側', 4),

    ('yawata_seitetsu_1901', 'th_kanto_dai_shinsai',
     'lore', '1923-09-01',
     '関東大震災と九州への人口流入',
     '1923年の関東大震災後、被災者の一部が九州へ移住。'
     '労働者街への新規流入が、戦後ヤクザ系列の母体の一つになった、と '
     '関連書籍は描く。',
     None, None, None, '戦後闇市', '市民側', 2),

    ('kokura_yamiichi_1946', 'th_wartime_kokura',
     'lore', '1937-1945',
     '戦時下の闇取引萌芽',
     '日中戦争・太平洋戦争期の物資統制下、小倉駅前・旦過周辺で '
     '闇取引が萌芽。戦後の闇市文化は戦時下の地下経済を直接の前史としている、と '
     '北九州市史は整理する。',
     None, None, None, '戦後闇市', '草野一家系', 3),

    ('yawata_seitetsu_1901', 'th_yawata_kushuu',
     'attack', '1944-08-19',
     '第1次八幡空襲 — 八幡製鐵所被弾',
     '米軍 B-29 による第1次八幡空襲。八幡製鐵所が初めて目視爆撃の標的に。'
     '日本本土への戦略爆撃の象徴的開始点。',
     '一般市民・労働者', '空襲', '死者多数', '戦後闇市', '市民側', 5),

    ('yawata_seitetsu_1901', 'th_yawata_kushuu',
     'attack', '1945-06-25',
     '第2次八幡空襲',
     '1945年6月25日、北九州中心部への大規模空襲。八幡・小倉・若松・戸畑が '
     '壊滅的被害。戦災での街区破壊が戦後闇市形成の物理的前提となった。',
     '一般市民', '空襲', '死者多数', '戦後闇市', '市民側', 5),

    ('kokura_air_raid_1945', 'th_kokura_kushuu',
     'attack', '1945-08-08',
     '小倉空襲',
     '1945年8月8日、小倉市街地への大規模空襲。中心部の街区が大きく失われ、'
     '戦後の街区再建の中で闇市と新しい街路が同時に形成されていく。',
     '一般市民', '空襲', '死者多数', '戦後闇市', '市民側', 5),

    ('kokura_air_raid_1945', 'th_kokura_kushuu',
     'lore', '1945-08-09',
     '第二原爆の本来の標的だった小倉',
     '1945年8月9日、米軍は当初、原子爆弾の投下標的を小倉(八幡製鐵所)とした。'
     'B-29「ボックスカー」は小倉上空で目視爆撃を試みたが、'
     '前日の空襲の煙と雲で目標が確認できず、第二目標の長崎へ変更。'
     '小倉が「原爆を免れた街」となった世界史的偶然。',
     None, None, None, '戦後闇市', '市民側', 5),

    ('kokura_yamiichi_1946', 'th_postwar_yamiichi',
     'lore', '1945-09-02',
     'GHQ 進駐と物資配給崩壊',
     '1945年9月、GHQ 進駐期に物資配給制度が事実上崩壊。'
     '小倉駅前・旦過周辺に大規模な闇市が形成され、'
     '北九州市民の食料・生活物資供給の現実的な中核となった。',
     None, None, None, '戦後闇市', '市民側', 4),

    ('kokura_yamiichi_1946', 'th_postwar_yamiichi',
     'lore', '1946-1950',
     '闇市最盛期 — 草野一家の母体',
     '1946-1950年は北九州闇市の最盛期。'
     'テキ屋系・博徒系の組織が闇市の場所代徴収・トラブル調停を担い、'
     '草野一家(1947結成)・後の工藤組(1953結成)の組織的基盤が形成された。',
     None, None, None, '戦後闇市', '草野一家系', 4),

    ('kokura_yamiichi_1946', 'th_chosen_sensou_tokuju',
     'lore', '1950-1953',
     '朝鮮戦争特需 — 北九州経済の復活',
     '朝鮮戦争特需(1950-1953)で八幡製鐵所をはじめとする北九州重工業が急速に復興。'
     '労働者街の経済が活性化し、組織犯罪も「働く者の街」と並走する形で再編。',
     None, None, None, '戦後闇市', '市民側', 3),

    ('yawata_iron_works_area', 'th_kitakyu_5shi_gappei',
     'designation', '1963-02-10',
     '北九州市発足 — 5市合併',
     '1963年2月10日、門司・小倉・八幡・若松・戸畑の5市が合併して北九州市が発足。'
     '政令指定都市となり、各地場ヤクザ系列の縄張りが「同一市内の異なる区」 '
     'という新しい行政枠組みに重ね合わされた。',
     None, None, None, '高度成長', '市民側', 4),

    # ===== 食文化 =====
    ('sasashi_udon_first', 'th_sasashi_history',
     'lore', '1976',
     '資さんうどん 1号店創業',
     '1976年、北九州市小倉南区で資さんうどん 1号店創業。'
     '深夜営業の庶民食堂として、繁華街帰り・労働者・地元住民が混在する場所となる。'
     '工藤會時代の「街の日常側」を象徴する拠点として、'
     '地元紙コラム・SNS で繰り返し語られる存在。',
     None, None, None, '高度成長', '市民側', 3),

    ('sasashi_udon_first', 'th_sasashi_history',
     'lore', '2024',
     '資さんうどん 全国展開 — 元北九州の味',
     '2024年、資さんうどんは関東への大規模展開を進めた。'
     '北九州の労働者街の味が全国に届く節目として地元紙に報じられた。',
     None, None, None, '解体後', '市民側', 2),

    ('horumon_district_sakaimachi', 'th_horumon_culture',
     'lore', '1950s-1980s',
     '堺町ホルモン — 仕事帰りの八幡労働者',
     '堺町のホルモン店街は、八幡製鐵所労働者の「仕事帰りに集まる場所」 '
     'として育った。安価で栄養価の高い内臓食が、重工業都市の食文化の核に。'
     '工藤會時代もこのエリアは庶民の食卓として機能し続けた。',
     None, None, None, '高度成長', '市民側', 3),

    ('kokura_yatai_corner', 'th_yatai_history',
     'lore', '1950s-1990s',
     '小倉駅前 屋台横丁の隆盛と消失',
     '戦後から平成初期まで、小倉駅前一帯に屋台横丁が存在。'
     '闇市文化の直接の継承で、屋台主の中には博徒系の縁を持つ者もいたと '
     '地元紙の回顧連載は記録する。再開発で姿を消したが、'
     '北九州の戦後文化の典型風景として記憶される。',
     None, None, None, '戦後闇市', '市民側', 3),

    # ===== 家族・女性・二世 =====
    ('kudokai_hq_kandake', 'th_yakuza_family_book',
     'lore', '1990s-2010s',
     '「ヤクザの女房」文化',
     'ヤクザの家族・特に妻の役割は実話誌・関連書籍で繰り返し描かれてきた。'
     '工藤會幹部の家族についても断片的に報じられているが、'
     '個人特定情報は本マップには載せない。家族視点は社会的孤立の側面として位置づけ。',
     None, None, None, '平成抗争', '工藤會', 2),

    ('kokura_higashi_school', 'th_2sei_school',
     'lore', '2014-2019',
     '二世問題 — 学校での孤立',
     '指定暴力団関係者の子どもが学校で経験する社会的孤立は、'
     '頂上作戦以降に複数の報道で取り上げられた。'
     '暴排運動の副作用として、家族の社会復帰支援の必要性が議論された。',
     None, None, None, '頂上作戦', '工藤會', 3),

    ('bouhai_center_fukuoka', 'th_njourney_kazoku',
     'lore', '2010s',
     '家族支援 — 離脱者の妻と子',
     '福岡県暴追運動推進センターは、組員本人の離脱支援と並んで、'
     '家族(特に妻と子)の社会復帰支援にも取り組んだ。'
     '「ヤクザの家族」のラベルから抜け出る難しさが、'
     'ドキュメンタリー番組でも記録された。',
     None, None, None, '頂上作戦', '市民側', 3),

    # ===== メディア・表象 =====
    ('crows_kitakyu_setting', 'th_crows_kitakyu_setting',
     'lore', '1990-2014',
     '高橋ヒロシ「クローズ」「Worst」と北九州',
     '高橋ヒロシは北九州市出身。代表作「クローズ」「Worst」の舞台「鈴蘭高校」は、'
     '北九州近隣がモデルとされる。'
     '工藤會時代の北九州の不良文化が、戦後ヤクザ文化と地続きで描かれた。'
     '映画化・実写化を経て、北九州=ヤクザ的不良文化の国際的アイコンに。',
     None, None, None, '平成抗争', '市民側', 4),

    ('crows_kitakyu_setting', 'th_crows_kitakyu_setting',
     'lore', '2007-2009',
     '映画「クローズZERO」「クローズZERO II」',
     '三池崇史監督の「クローズZERO」シリーズ(2007・2009)で、'
     '高橋ヒロシの世界観が映像化。'
     '工藤會時代の北九州の不良文化が日本全国・アジアに広まる転機となった。',
     None, None, None, '平成抗争', '市民側', 3),

    ('mojiport_kitagata_book', 'th_kitagata_bloody_doll',
     'lore', '1985-1996',
     '北方謙三「ブラディ・ドール」シリーズ',
     '北方謙三のハードボイルド連作。門司港のバー「ブラディ・ドール」を舞台に、'
     '関門地区の組織犯罪文化を描く。1985-1996年に多数刊行。'
     '戦後港町の暗部の文学化として、北方文学の代表作の一つ。',
     None, None, None, '高度成長', '工藤組系', 3),

    ('ryugagotoku_virtual', 'th_ryugagotoku_sega',
     'lore', '2005-',
     '「龍が如く」シリーズと国際的ヤクザ表象',
     'セガ「龍が如く」シリーズは2005年初代以降、20作以上が発売・累計2000万本以上。'
     '架空の「神室町」(歌舞伎町モデル)を舞台に、'
     '指定暴力団時代のヤクザ文化を国際的に広めた最重要作品。'
     'Tokyo Vice と並んで、海外の Kudo-kai 認知の素地を作った。',
     None, None, None, '平成抗争', '工藤會', 4),

    ('kudokai_hq_kandake', 'th_yakuza_enka',
     'lore', '1960s-1990s',
     '演歌・歌謡曲の任侠表象',
     '美空ひばり・北島三郎・八代亜紀・鶴田浩二らの楽曲には、'
     '任侠的世界観を描いた歌が多数。直接 Kudo-kai を歌うものはないが、'
     '日本社会の任侠文化の受容を作った文脈として参照される。',
     None, None, None, '高度成長', '市民側', 2),

    ('kudokai_hq_kandake', 'th_yakuza_manga_general',
     'lore', '1960s-',
     'ヤクザ漫画の系譜 — 劇画から現代まで',
     'ヤクザ漫画は1960年代の劇画黄金期から現代まで継続。'
     '「あぶさん」「ミナミの帝王」「ナニワ金融道」「闇金ウシジマくん」「ザ・ファブル」 '
     '「サンクチュアリ」など、各時代の社会観を反映する作品が登場。'
     '工藤會時代の表象は南勝久「ザ・ファブル」(2014-)に最も濃く反映。',
     None, None, None, '平成抗争', '著作者', 3),

    ('magazine_tsukuru', 'th_jitsuwa_special',
     'lore', '1990s-',
     '月刊『創』 — 工藤會特集の系譜',
     '月刊『創』は社会派雑誌として工藤會を含む指定暴力団の特集を継続的に組んできた。'
     '頂上作戦・本部解体・判決の各節目で長尺特集を掲載。'
     '報道書籍と地元紙の中間を埋める情報源として機能している。',
     None, None, None, '平成抗争', '著作者', 3),

    ('kudokai_hq_kandake', 'th_fabel_manga',
     'lore', '2014-',
     '南勝久「ザ・ファブル」— 引退ヤクザの世界',
     '2014年連載開始の「ザ・ファブル」は引退した殺し屋の物語。'
     '暴対法時代・特定危険指定時代の「ヤクザが普通の社会に戻れない」状況を '
     '間接的に背景にした作品として、工藤會研究と並列で語られる。',
     None, None, None, '頂上作戦', '工藤會', 3),

    ('kudokai_hq_kandake', 'th_outrage_kitano',
     'lore', '2010-2017',
     '北野武「アウトレイジ」シリーズの影響',
     '北野武の「アウトレイジ」シリーズ(2010・2012・2017の3部作)は、'
     '暴対法時代の組織犯罪を残虐美の様式で描いた。'
     '工藤會を直接の素材としないが、暴対法時代のヤクザ表象の '
     '海外的アイコン化に大きく寄与。',
     None, None, None, '平成抗争', '工藤會', 3),

    # ===== 全国比較 =====
    ('compare_yamaguchigumi_hq', 'th_yamaguchigumi_history',
     'lore', '1915-2024',
     '六代目山口組 — 全国最大の指定暴力団',
     '神戸市灘区に総本部を置く六代目山口組は全国最大の指定暴力団。'
     '1915年起源と110年以上の歴史を持つ。工藤會とは別系統で、'
     '工藤會のような市民威迫の手口は組織的に取られていない。',
     None, None, None, '高度成長', '山口組系', 3),

    ('compare_sumiyoshi_hq', 'th_sumiyoshikai_history',
     'lore', '1958-',
     '住吉会 — 関東の地場連合体',
     '東京・関東を本拠とする指定暴力団 住吉会。'
     '山口組と並ぶ全国2強の片翼で、関東の地場連合体の代表。'
     '工藤會とは縄張り・系統・手口がほぼ重ならない。',
     None, None, None, '高度成長', '司法側', 2),

    ('compare_inagawakai_hq', 'th_inagawakai_history',
     'lore', '1949-',
     '稲川会 — 神奈川を中心とする組織',
     '神奈川・東京を中心とする指定暴力団 稲川会。'
     '1949年起源で、戦後ヤクザ史の主要組織の一つ。'
     '工藤會とは地理・系統が異なるが、全国 OSINT の比較対象として並列。',
     None, None, None, '高度成長', '司法側', 2),

    ('compare_aizukotetsu_hq', 'th_aizukotetsu_history',
     'lore', '1869-',
     '会津小鉄会 — 明治期からの京都地場組織',
     '京都を本拠とする指定暴力団 会津小鉄会。'
     '1869年起源と日本最古級のヤクザ系統。'
     '関西地場連合体として、九州とは別系統で論じられる。',
     None, None, None, '戦後闇市', '司法側', 2),

    ('compare_kyokutokai_hq', 'th_kyokutokai_tekiya',
     'lore', '1950s-',
     '極東会 — 関東テキ屋系の系譜',
     '関東を中心とする指定暴力団 極東会。テキ屋系の系譜で、'
     '工藤會のような博徒+地場連合体とは異なる起源を持つ。'
     '日本のヤクザ系統の多様性を示す代表事例。',
     None, None, None, '高度成長', '司法側', 2),

    ('compare_namikawakai_hq', 'th_namikawakai_kyushu',
     'lore', '2013-',
     '浪川会 — 九州抗争の継承',
     '2013年、九州誠道会の解散届を受けて再編された浪川会。'
     '久留米を中心とする九州地場ヤクザの一翼。'
     '工藤會とは別系統だが、九州ヤクザ史の文脈で並列で語られる。',
     None, None, None, '解体後', '道仁会系', 3),

    ('compare_kyokuseikai_hq', 'th_kyokuseikai_hiroshima',
     'lore', '1963-',
     '共政会 — 広島ヤクザ史の中核',
     '広島を本拠とする指定暴力団 共政会。'
     '「孤狼の血」シリーズの背景となる広島ヤクザ史を構成する組織。'
     '工藤會研究と並列で「中国地方の暴対法対応」の比較対象として参照。',
     None, None, None, '高度成長', '司法側', 3),

    ('compare_kyokuryukai_hq', 'th_kyokuryukai_okinawa',
     'lore', '1949-',
     '旭琉会 — 沖縄の特殊な戦後史',
     '沖縄県を本拠とする指定暴力団 旭琉会。米軍統治・本土復帰の特殊な歴史背景を持つ。'
     '全国の指定暴力団の中でも独自の系統。',
     None, None, None, '戦後闇市', '司法側', 2),

    # ===== 国際比較 =====
    ('intl_cosa_nostra_italy', 'th_cosa_nostra_book',
     'war', '1860s-',
     'シチリア コーザ・ノストラ — 国際比較の基準',
     'シチリアを本拠とするイタリアマフィア コーザ・ノストラは、'
     '組織犯罪研究の比較基準。家族(ファミリー)単位の構成、'
     '血縁ベースの結束、行政府への浸透などが、'
     '工藤會研究の比較対象として参照される。',
     None, None, None, '戦後闇市', '司法側', 4),

    ('intl_ndrangheta_italy', 'th_ndrangheta_book',
     'war', '1860s-',
     '\'ンドランゲタ — 現代の最強マフィア',
     '南イタリア・カラブリア州の \'ンドランゲタは現在のイタリア最強のマフィア。'
     'コカイン取引でグローバルに展開。'
     '工藤會研究の比較では「現代的な暴力管理」の対比対象として参照される。',
     None, None, None, '解体後', '司法側', 4),

    ('intl_triads_hk', 'th_hk_triads',
     'war', '1700s-',
     '香港 三合会 — アジア組織犯罪研究',
     '香港の三合会は中国系犯罪組織群の総称。「14K」「和勝和」などの大組織を含む。'
     'アジア組織犯罪研究で工藤會と並列で参照される代表事例。',
     None, None, None, '戦後闇市', '司法側', 3),

    ('intl_la_cosa_nostra_us', 'th_us_lcn_fbi',
     'war', '1900s-',
     '米国 La Cosa Nostra — RICO 法の歴史',
     '米国マフィア La Cosa Nostra(LCN)に対する FBI の継続的捜査と、'
     '1970年 RICO 法に基づく組織トップ立件のモデルは、'
     '工藤會頂上作戦の捜査方針(組織トップへの首謀者責任追及)の '
     '直接的な比較対象として参照される。',
     None, None, None, '戦後闇市', '司法側', 4),

    ('intl_mekong_compounds_ref', 'th_mekong_compounds',
     'war', '2018-',
     'メコン詐欺コンパウンド — 現代の組織犯罪',
     'ミャンマー・カンボジア国境のオンライン詐欺コンパウンド群は '
     '現代の組織犯罪の新しい形。本マップの姉妹プロジェクト「Compound Time Machine」 '
     'がカバー。日本のヤクザの国際展開とは別系統だが、'
     '組織犯罪 OSINT の現代的対象として並列参照される。',
     None, None, None, '解体後', '司法側', 4),

    ('kudokai_hq_kandake', 'th_rankin_comparative',
     'lore', '2010s-',
     'Rankin の比較研究 — 工藤會の独自性',
     'ケンブリッジ大の Andrew Rankin ら海外研究は、工藤會を '
     '「日本で唯一市民を直接標的とする指定暴力団」として、'
     'イタリアマフィアの市民暴力との比較で論じる。'
     '国際的に見ても極めて独自の組織犯罪事例とされる。',
     None, None, None, '解体後', '工藤會', 3),

    # ===== 金融・反社対応 =====
    ('zenginkyo_compliance', 'th_finance_2007',
     'designation', '2007-06',
     '政府指針(2007)— 企業による反社遮断',
     '2007年6月、政府が「企業が反社会的勢力との関係を遮断するための指針」を策定。'
     '銀行・証券・保険・不動産・通信などの主要業界の反社対応の起点。',
     None, None, None, '平成抗争', '司法側', 4),

    ('zenginkyo_compliance', 'th_finance_2011',
     'designation', '2011',
     '反社条項の標準化',
     '2011年、全国銀行協会・各業界団体が反社条項の標準化を推進。'
     '取引約款への反社条項組み込みが事実上義務化された。'
     '指定暴力団関係者の銀行口座開設・取引が法的に困難に。',
     None, None, None, '平成抗争', '司法側', 4),

    ('mizuho_bank_hq', 'th_mizuho_2013',
     'extortion', '2013',
     'みずほ銀行 反社融資問題',
     '2013年、みずほ銀行が暴力団関係先に約230件の融資を行っていたことが表面化。'
     '内部チェックの不備が露呈し、銀行業界全体の反社チェック体制の根本見直しの '
     '契機となった事案。',
     '銀行(社会的損失)', None, '行政処分', '平成抗争', '司法側', 4),

    ('mizuho_bank_hq', 'th_mizuho_2013',
     'ruling', '2014',
     'みずほ銀行 業務改善命令',
     '2014年、金融庁がみずほ銀行に業務改善命令。'
     '銀行業界の反社チェック体制が一斉に厳格化され、'
     '指定暴力団との金融関係の遮断が大幅に進んだ。',
     None, None, None, '平成抗争', '司法側', 3),

    ('zenginkyo_compliance', 'th_crypto_aml',
     'designation', '2018-',
     '暗号資産取引所の反社対応',
     '2018年以降、金融庁が暗号資産交換業者の反社チェック・AML 対応を強化。'
     '指定暴力団関係者の暗号資産取引所利用も口座開設段階で遮断される枠組みが '
     '整備された。',
     None, None, None, '解体後', '司法側', 3),
]


# ord, site_slug, year, title, body, spice, era_tag, faction_tag, source_key
LORE = [
    (1000, 'kokura_air_raid_1945', '1945-08-09',
     '「もし雲がなかったら」— 小倉と長崎の運命',
     '1945年8月9日、米軍 B-29「ボックスカー」が小倉上空で目視爆撃を試みた。'
     '前日の小倉空襲の煙と当日の雲で目標が確認できず、'
     '第二目標の長崎へ変更された。'
     '「もし雲がなかったら」小倉が原爆投下都市になっていた歴史的偶然は、'
     '北九州の戦後文化全体の前提となっている。',
     5, '戦後闇市', '市民側', 'th_kokura_kushuu'),

    (1010, 'kokura_yamiichi_1946', '1946-1950',
     '闇市の場所代徴収 — 戦後の「もうひとつの統治」起源',
     '戦後闇市では、土地所有者不明・GHQ 統制外の場所で大規模な市が立った。'
     '場所代徴収・トラブル調停・露店配置の管理は地場の博徒・テキ屋系が担い、'
     'これが後の草野一家・工藤組の組織的基盤になった。'
     '「もうひとつの統治」起源として戦後ヤクザ史研究で重要視される。',
     5, '戦後闇市', '草野一家系', 'th_postwar_yamiichi'),

    (1020, 'yawata_seitetsu_1901', '1901-1945',
     '八幡製鐵所と労働者街文化の蓄積',
     '1901年から半世紀以上にわたる八幡製鐵所の操業は、'
     '北九州に独特の労働者街文化を蓄積した。'
     '飯場・遊郭・酒場・賭場が同心円状に並ぶ重工業都市の構造は、'
     '戦後ヤクザ系列の地理的基盤になった、と組織犯罪研究は整理する。',
     4, '戦後闇市', '市民側', 'th_yawata_seitetsu_history'),

    (1030, 'sasashi_udon_first', '1976-2024',
     '資さんうどん — 「街の日常側」の象徴',
     '小倉発祥の資さんうどんは、深夜営業の庶民食堂として、'
     '繁華街帰り・労働者・警察官・暴排運動関係者・地元住民が混在する場所だった。'
     '工藤會時代の北九州を語る地元紙コラムには '
     '「資さんうどんで暴排を語る記者」という風景が繰り返し登場する。',
     4, '頂上作戦', '市民側', 'th_sasashi_history'),

    (1040, 'horumon_district_sakaimachi', '1950s-',
     '堺町ホルモン — 労働者と組と客が同じテーブル',
     '堺町のホルモン店街は、八幡製鐵所労働者・地元住民・組関係者が '
     '同じテーブルに座る場所だった。'
     '高度成長期の北九州の食文化は、組織犯罪と労働文化と庶民文化が '
     '物理的に分離されない、独特の混在を示してきた。',
     4, '高度成長', '市民側', 'th_horumon_culture'),

    (1050, 'kokura_yatai_corner', '1950s-1990s',
     '小倉駅前 屋台横丁の最後の夜',
     '平成初期の再開発で消えた小倉駅前の屋台横丁。'
     '撤去前夜には、最後の屋台で杯を交わす地元客の絵が地元紙に残る。'
     '戦後闇市から続く文化が、平成の都市再生で姿を消した節目。',
     4, '高度成長', '市民側', 'th_yatai_history'),

    (1060, 'crows_kitakyu_setting', '1990-2014',
     '高橋ヒロシ — 北九州の不良文化を漫画化',
     '北九州市出身の高橋ヒロシは、地元の不良文化を「クローズ」「Worst」で漫画化。'
     '工藤會時代の北九州の若年層文化が、ヤクザの世界と地続きにあった事実を、'
     '直接ヤクザを描かずに伝える間接的なドキュメントとして機能した。',
     5, '平成抗争', '市民側', 'th_crows_kitakyu_setting'),

    (1070, 'mojiport_kitagata_book', '1985-1996',
     '北方謙三 — 門司港の暗部の文学化',
     '北方謙三の「ブラディ・ドール」シリーズは、門司港のバーを舞台にした '
     '連作ハードボイルド。1985年から1996年まで複数巻刊行。'
     '関門海峡の港町と組織犯罪文化の関係を、'
     '報道書籍では届かない情感の領域で記録した文学的成果。',
     4, '高度成長', '工藤組系', 'th_kitagata_bloody_doll'),

    (1080, 'ryugagotoku_virtual', '2005-2024',
     '「龍が如く」と Tokyo Vice — 海外受容の二本柱',
     'セガ「龍が如く」(2005-)と Jake Adelstein「Tokyo Vice」(2009-)は、'
     '海外視聴者・読者向けに日本のヤクザ文化を広めた二本柱。'
     '工藤會の特定危険指定が海外メディアで広く認知される素地は、'
     'この二本柱で作られた。',
     4, '頂上作戦', '工藤會', 'th_ryugagotoku_sega'),

    (1090, 'compare_yamaguchigumi_hq', '2015-',
     '山口組分裂 vs 工藤會頂上作戦 — 並走する2つの圧力',
     '2015年の神戸山口組分裂と2014年の工藤會頂上作戦は、'
     '指定暴力団情勢に並走する2つの圧力。'
     '一方は「内部分裂による弱体化」、もう一方は「司法による弱体化」 — '
     '日本の組織犯罪情勢の2010年代後半の特徴を示す対比。',
     4, '頂上作戦', '山口組系', 'th_yamaguchigumi_history'),

    (1100, 'intl_la_cosa_nostra_us', '1970-2024',
     'RICO 法と頂上作戦 — 50年の時差',
     '米国 RICO 法(1970)は組織トップを共謀罪で立件する道筋を開いた。'
     '日本の頂上作戦(2014)は同様の発想を50年の時差で実装した形になる。'
     '法学者は両者の射程と限界を比較で論じる。',
     4, '頂上作戦', '司法側', 'th_us_lcn_fbi'),

    (1110, 'intl_mekong_compounds_ref', '2020-',
     'メコンコンパウンド — 現代の組織犯罪の新形態',
     'メコン地域のオンライン詐欺コンパウンドは、'
     '「物理的拠点 + 国境跨ぎ + 監禁労働 + 暗号資産」という '
     '21世紀型の組織犯罪。'
     '日本のヤクザ系列が直接関与する事例はほぼ報じられていないが、'
     '組織犯罪 OSINT 研究の現代的対象として並列参照される。',
     4, '解体後', '司法側', 'th_mekong_compounds'),

    (1120, 'mizuho_bank_hq', '2013-2014',
     'みずほ事件と銀行界の革命',
     'みずほ銀行 反社融資問題の発覚と業務改善命令は、'
     '日本の銀行業界の反社チェック体制を「やる気のあるところからやる」 '
     '段階から「やらないと許されない」段階へ押し上げた。'
     '指定暴力団の金融遮断の決定打になった事件。',
     4, '平成抗争', '司法側', 'th_mizuho_2013'),

    (1130, 'kudokai_hq_kandake', '2014-',
     '南勝久「ザ・ファブル」と引退の様式',
     '2014年連載開始の「ザ・ファブル」は、引退した殺し屋を主人公にする。'
     '指定暴力団時代の「ヤクザが普通の社会に戻れない」状況を背景にする漫画として、'
     '工藤會傘下の離脱者支援の現実と通底する。'
     '頂上作戦と同時期の連載開始は偶然ではない、と漫画評論は指摘する。',
     3, '頂上作戦', '著作者', 'th_fabel_manga'),

    (1140, 'kokura_higashi_school', '2014-2019',
     '二世の進路 — 「変えてはいけない」と「変えなければ」',
     'ヤクザ二世の進路をめぐる家族・教師・地域の葛藤は、'
     '頂上作戦以降の地元紙の連載に繰り返し登場する。'
     '「親の世界を継ぐな」「親を尊敬する子の権利」という二つのモーダルが '
     '同じ家族の中で衝突するナラティブ。',
     3, '頂上作戦', '工藤會', 'th_2sei_school'),

    (1150, 'magazine_tsukuru', '2014-2024',
     '月刊『創』— 工藤會10年連載',
     '頂上作戦から10年間、月刊『創』は工藤會関連の特集を断続的に組んだ。'
     '報道書籍のような体系性はないが、地元紙より広く全国紙より狭い '
     '独自の射程で、検察・元組員・家族・周辺事業者の証言を継続収集した。',
     3, '頂上作戦', '著作者', 'th_jitsuwa_special'),

    (1160, 'compare_kyokuseikai_hq', '2018-',
     '「孤狼の血」と広島・北九州の暗号交換',
     '柚月裕子原作・役所広司主演「孤狼の血」シリーズの広島と、'
     '工藤會頂上作戦の北九州は、暴対法時代の地方都市と組織犯罪の '
     '同時代記録として読者の間で並列参照される。'
     '広島の共政会と北九州の工藤會は、別系統だが同じ時代の地殻変動の中にいた。',
     4, '頂上作戦', '司法側', 'th_kyokuseikai_hiroshima'),

    (1170, 'compare_kyokuryukai_hq', '1972-',
     '本土復帰と沖縄のヤクザ — 工藤會とは違う特殊性',
     '1972年の沖縄本土復帰前後の旭琉会など沖縄系ヤクザは、'
     '米軍統治下での独自の発展を経た。'
     '工藤會の九州地場連合体形成とは別の経路で生まれた組織群として、'
     '日本のヤクザ系統の多様性を示す。',
     3, '高度成長', '司法側', 'th_kyokuryukai_okinawa'),

    (1180, 'intl_cosa_nostra_italy', '1992-',
     'ファルコーネ判事とイタリアの暴対 — 日本との比較',
     'イタリアでは1992年にファルコーネ判事がマフィアの爆弾事件で殺害された後、'
     '反マフィア法制が大幅に強化された。'
     '日本の暴対法(1991)・特定危険指定(2012)は、'
     'イタリアの経験を一部参照したと法学者は指摘する。',
     4, '高度成長', '司法側', 'th_cosa_nostra_book'),

    (1190, 'kudokai_hq_kandake', '1990s-2024',
     '雑誌『創』編集長の語り',
     '月刊『創』編集長は、ヤクザ取材を「社会の周縁にしか見えない真実を伝える」 '
     'と位置づけてきた。'
     '工藤會を含む特定危険指定の長期取材は、報道書籍と地元紙の隙間を埋める '
     'メディアの役割の典型例として、ジャーナリズム研究にも参照される。',
     3, '解体後', '著作者', 'th_jitsuwa_special'),

    (1200, 'kudokai_hq_kandake', '1945-2024',
     '79年を貫く小倉中心市街 — 戦災・闇市・本部・解体',
     '1945年の小倉空襲から2019年の工藤會本部解体まで、'
     '小倉中心市街は79年の間に「戦災の街・闇市の街・組の街・暴排の街」と '
     '何度も性格を変えた。'
     'その全ての層が、現在も街の地理に重なっている。',
     5, '解体後', '市民側', 'th_postwar_yamiichi'),
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
    print(f'phase18_thicker: +{ev_inserted} events, +{lr_inserted} lore')
    if missing:
        print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
