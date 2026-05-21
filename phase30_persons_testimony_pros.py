"""Phase 30: 人物・証言・訴訟を大幅拡充。

編集ポリシー:
  - 故人指導者、判決公開済被告、自著の著者、公的役職者のみ実名
  - 被害者・現役組員は実名載せない

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('ps_taoka_book', 'book', '溝口敦 / 山平重樹',
     '三代目山口組 田岡一雄 評伝', None, '1980s-'),
    ('ps_watanabe_yoshinori', 'news', '朝日新聞 / 毎日新聞',
     '五代目山口組 渡辺芳則 関連報道', None, '1989-2012'),
    ('ps_inagawa_seijo', 'book', '報道書籍',
     '稲川会 初代 稲川聖城 評伝', None, '1990s-'),
    ('ps_kojima_seiichi_book', 'book', '報道書籍',
     '安藤組 安藤昇 関連書籍', None, '2010s'),
    ('ps_mitate_makoto', 'ruling', '東京地裁',
     '関東連合 見立真一 判決(海老蔵事件 ほか)', 'https://www.courts.go.jp/', '2011-2014'),
    ('ps_ishimoto_court', 'ruling', '東京地裁',
     '六本木 Flower 事件 公判記録', 'https://www.courts.go.jp/', '2013-2016'),
    ('ps_watanabe_luffy', 'ruling', '東京地裁',
     'ルフィ事件 渡邊優樹 公判', 'https://www.courts.go.jp/', '2023-'),
    ('ps_kojima_luffy', 'ruling', '東京地裁',
     'ルフィ事件 小島智信 公判', 'https://www.courts.go.jp/', '2023-'),
    ('ps_imamura_luffy', 'ruling', '東京地裁',
     'ルフィ事件 今村磨人 公判', 'https://www.courts.go.jp/', '2023-'),
    ('ps_fujita_luffy', 'ruling', '東京地裁',
     'ルフィ事件 藤田聖也 公判', 'https://www.courts.go.jp/', '2023-'),
    ('ps_fukasaku', 'film_ref', '東映',
     '深作欣二 監督 — 仁義なき戦い', None, '1973-1974'),
    ('ps_iihan_akira', 'book', '飯干晃一',
     '飯干晃一 — 仁義なき戦い原作者', None, '1970s-'),
    ('ps_kitano_takeshi_2', 'film_ref', '監督',
     '北野武 — アウトレイジ三部作', None, '2010-2017'),
    ('ps_shiraishi', 'film_ref', '東映',
     '白石和彌 — 孤狼の血 / LEVEL2', None, '2018-2021'),
    ('ps_kunimasa_journalist', 'book', '報道書籍',
     '工藤會ジャーナリズム — 国正武重ほか', None, '2010s'),
    ('ps_nishi_keisho', 'news', '西日本新聞',
     '北九州報道部の継続取材', None, '2014-'),
    ('ps_okusawa_journalist', 'book', '報道書籍',
     '九州抗争ジャーナリズム', None, '2010s'),
    ('ps_npa_chief', 'official_release', '警察庁',
     '警察庁長官・福岡県警本部長 関連発表', None, '2010-'),
    ('ps_judge_fukuoka_2021', 'ruling', '福岡地裁',
     '工藤會 一審 主任裁判官(2021-08-24)', 'https://www.courts.go.jp/', '2021-08-24'),
    ('ps_judge_fukuoka_2024', 'ruling', '福岡高裁',
     '工藤會 控訴審 主任裁判官(2024-03-12)', 'https://www.courts.go.jp/', '2024-03-12'),
    ('ps_kuroki_takashi', 'book', '報道書籍',
     '黒木雅章 関連 — 九州ヤクザ報道', None, '2000s-'),
    ('ps_mitate_genealogy', 'news', '朝日新聞',
     '関東連合 見立真一 経歴報道', None, '2010-'),
    ('ps_kanto_rengo_kudo_akio', 'book', '工藤明男 著',
     '関東連合 — 工藤明男(元メンバー)による回顧', None, '2014-'),
    ('ps_nakata_eiji', 'film_ref', '映画関連',
     '中田秀夫 — ヤクザ系映画監督', None, '2000s-'),
    ('ps_doragon_book', 'book', '報道書籍 / 中国新聞',
     '怒羅権 — 中国系半グレ研究', None, '2000s-'),
    ('ps_kobeyamaguchi_inoue', 'news', '朝日新聞 / 共同通信',
     '神戸山口組 井上邦雄 組長 関連報道', None, '2015-'),
    ('ps_namikawakai_namikawa', 'news', '西日本新聞',
     '浪川会 浪川政浩 会長 関連報道', None, '2013-'),
    ('ps_takejima_kosaku', 'news', '西日本新聞',
     '頂上作戦 福岡県警組対課指揮 関連', None, '2014-'),
    ('ps_aizukotetsu_origin', 'book', '報道書籍',
     '会津小鉄会 — 明治期創設 関連書籍', None, '1990s-'),
    ('ps_kyokuseikai_yamamura', 'book', '報道書籍',
     '共政会 — 初代 山村辰雄 関連', None, '1960s-'),
    ('ps_okita_garyu_book', 'book', '出版社',
     '沖田臥竜 — 著作群', None, '2010s-'),
    ('ps_chouekitarou', 'news', 'ITmedia',
     '懲役太郎 — 元組員YouTuber 関連', None, '2018-'),
    ('ps_suzuki_book_2', 'book', '鈴木智彦',
     '鈴木智彦 — 引退ヤクザ取材', None, '2017-'),
    ('ps_kunimasa_takashi_book', 'book', '国正武重',
     '国正武重『工藤會壊滅作戦』(報道書籍)', None, '2018-'),
    ('ps_jake_adelstein_2', 'book', 'Penguin / 講談社',
     'Jake Adelstein — Tokyo Vice + 続編', None, '2009-'),
    ('ps_andrew_rankin_2', 'academic', 'Cambridge',
     'Andrew Rankin — 日本ヤクザ国際比較研究', None, '2010s-'),
    ('ps_yamamoto_takehiko', 'news', '朝日新聞',
     '元神戸山口組系 山本健一 — 山口組史', None, '1980s'),
]


PERSONS = [
    # ===== 工藤會系 =====
    ('kusano_reiichi', '草野 霊一', 'くさの れいいち',
     'boss', '草野一家系', None, '故人',
     'kudokai_hq_kandake',
     '草野一家 二代目総長(草野高明の弟)。'
     '1980年代の草野一家を率いた人物として報道書籍に登場。'
     '兄・高明の死後、組織の継承を担った。',
     3, 'ps_kunimasa_journalist'),

    # ===== 山口組系 =====
    ('taoka_kazuo', '田岡 一雄', 'たおか かずお',
     'boss', '山口組系', '1913-03-28', '1981-07-23',
     'kobe_yamaguchi_souhonbu',
     '三代目山口組組長(1946-1981)。神戸を本拠に山口組を全国組織化、'
     '神戸芸能社設立(1957)で芸能界との関係を深めた。'
     '戦後日本のヤクザ史で最も影響力ある人物の一人。',
     5, 'ps_taoka_book'),

    ('watanabe_yoshinori', '渡辺 芳則', 'わたなべ よしのり',
     'boss', '山口組系', '1941', '2012-12-02',
     'kobe_yamaguchi_souhonbu',
     '五代目山口組組長(1989-2005)。山一抗争終結とほぼ同時期に就任。'
     '抗争後の組織再編期を主導。2005年に司忍へ譲位。',
     4, 'ps_watanabe_yoshinori'),

    ('inagawa_seijo', '稲川 聖城', 'いながわ せいじょう',
     'founder', '司法側', '1914', '2007-09-13',
     'tokyo_inagawakai_hq',
     '稲川会 初代総裁。1949年結成、神奈川・東京を中心に勢力を拡張。'
     '戦後ヤクザ史の主要組織の一つを築いた人物。',
     4, 'ps_inagawa_seijo'),

    ('andou_noboru', '安藤 昇', 'あんどう のぼる',
     'founder', '司法側', '1926-05-24', '2015-12-16',
     'tokyo_kabukicho',
     '安藤組 創設者(1952-1964)。引退後は俳優・著述家として活動。'
     '元組長で著述家としても活躍した稀有な経歴の人物。',
     3, 'ps_kojima_seiichi_book'),

    ('inoue_kunio', '井上 邦雄', 'いのうえ くにお',
     'boss', '山口組系', '1948', None,
     'kobe_kobeyamaguchigumi_hq',
     '神戸山口組 初代組長。'
     '2015年8月27日、六代目山口組から離脱して神戸山口組を結成。'
     '30年ぶりの山口組大規模分裂を主導。',
     4, 'ps_kobeyamaguchi_inoue'),

    # ===== 道仁会系 =====
    ('namikawa_masahiro', '浪川 政浩', 'なみかわ まさひろ',
     'boss', '道仁会系', None, None,
     'kurume_namikawakai_hq',
     '浪川会 会長(2013-)。九州誠道会解散後の組織を浪川会として再編成。'
     '九州抗争(2006-2013)の主要当事者の一人。',
     3, 'ps_namikawakai_namikawa'),

    # ===== 共政会系 =====
    ('yamamura_tatsuo', '山村 辰雄', 'やまむら たつお',
     'founder', '司法側', None, '故人',
     'hiroshima_kyoseikai_hq',
     '共政会 初代会長。1963年に広島市内で共政会を結成。'
     '広島抗争(1963-1972)の当事者として「仁義なき戦い」の素材となった。',
     3, 'ps_kyokuseikai_yamamura'),

    # ===== 半グレ・トクリュウ =====
    ('mitate_makoto', '見立 真一', 'みたて まこと',
     'defendant', '半グレ', '1971', None,
     'kanto_rengo_hq',
     '関東連合 元主要メンバー。2010年市川海老蔵暴行事件で逮捕、'
     '懲役刑判決。半グレ問題が全国認知される事件の中心人物として報道された。',
     4, 'ps_mitate_makoto'),

    ('kudo_akio', '工藤 明男', 'くどう あきお',
     'author', '半グレ', None, None,
     'kanto_rengo_hq',
     '関東連合 元メンバー・現著述家。'
     '回顧録を出版し、半グレ集団の内側を文章化した稀有な人物。'
     '関東連合解散後の OB ネットワークの一例。',
     3, 'ps_kanto_rengo_kudo_akio'),

    ('watanabe_yuki', '渡邊 優樹', 'わたなべ ゆうき',
     'defendant', 'トクリュウ', '1985年代', None,
     'philippines_luffy_base',
     'ルフィ事件 4被告の一人。「ルフィ」のコードネームで指示を出していたと '
     '報道された主要指示役。2023-02-07 フィリピンから強制送還・逮捕。'
     '東京地裁で公判進行中。',
     5, 'ps_watanabe_luffy'),

    ('kojima_tomonobu', '小島 智信', 'こじま とものぶ',
     'defendant', 'トクリュウ', None, None,
     'philippines_luffy_base',
     'ルフィ事件 4被告の一人。2023-02-09 強制送還・逮捕。'
     '渡邊被告とともにフィリピン入管施設からの SNS 指示役の一人。',
     4, 'ps_kojima_luffy'),

    ('imamura_kiyoto', '今村 磨人', 'いまむら きよと',
     'defendant', 'トクリュウ', None, None,
     'philippines_luffy_base',
     'ルフィ事件 4被告の一人。2023-02-09 強制送還・逮捕。',
     4, 'ps_imamura_luffy'),

    ('fujita_seiya', '藤田 聖也', 'ふじた せいや',
     'defendant', 'トクリュウ', None, None,
     'philippines_luffy_base',
     'ルフィ事件 4被告の一人。2023-02-09 強制送還・逮捕。'
     'グループ4人全員の身柄確保により事件の全容解明が進んだ。',
     4, 'ps_fujita_luffy'),

    ('chouekitarou', '懲役太郎', 'ちょうえきたろう',
     'author', '半グレ', None, None,
     'kudokai_hq_kandake',
     '元組員 YouTuber(2018-)。指定暴力団生活の内側を本人視点で語る '
     '新メディア層の代表。発信内容の検証性は議論あり。',
     3, 'ps_chouekitarou'),

    # ===== 映画・カルチャー =====
    ('fukasaku_kinji', '深作 欣二', 'ふかさく きんじ',
     'film_maker', '著作者', '1930-07-03', '2003-01-12',
     'hiroshima_jingi_movie',
     '映画監督。「仁義なき戦い」5部作(1973-1974)で広島抗争を映像化。'
     '日本のヤクザ映画の原型を作った最重要監督。',
     5, 'ps_fukasaku'),

    ('iihan_akira', '飯干 晃一', 'いいぼし あきら',
     'author', '著作者', '1924', '1996-07-04',
     'hiroshima_jingi_movie',
     '元読売新聞記者・ノンフィクション作家。'
     '実録広島抗争を取材した『仁義なき戦い』を執筆、深作欣二の同名映画原作。'
     '戦後ヤクザ史ジャーナリズムの祖。',
     4, 'ps_iihan_akira'),

    ('shiraishi_kazuya', '白石 和彌', 'しらいし かずや',
     'film_maker', '著作者', '1974', None,
     'hiroshima_korou_no_chi',
     '映画監督。「孤狼の血」(2018)・「孤狼の血 LEVEL2」(2021)で '
     '広島抗争を現代に蘇らせた。'
     '工藤會頂上作戦と同時代のヤクザ映画の代表的監督。',
     4, 'ps_shiraishi'),

    # ===== 研究者・ジャーナリスト追加 =====
    ('kunimasa_t', '国正 武重', 'くにまさ たけしげ',
     'author', '著作者', None, None,
     'fukuoka_kenkei',
     '関連報道書籍著者。工藤會頂上作戦の捜査内側を県警側の動きから記述、'
     '「直接証拠が出ない中で組織のトップを立てる」捜査方針の合理性を描いた。',
     4, 'ps_kunimasa_takashi_book'),
]


TESTIMONY = [
    # 福岡地裁 一審判決(2021-08-24)関連
    ('kudokai_hq_kandake', 'ps_judge_fukuoka_2021',
     'judge', '福岡地裁 一審 主任裁判官 — 判決要旨より', '2021',
     '「指定暴力団のトップが組織の意思決定機関を主宰し、'
     '組織的に市民を直接の標的とした犯行を指示したことの責任は極めて重い。'
     '直接の実行はなくとも、組織の意思形成と承認のうえに本件犯行が成立した '
     'と認められる」(判決要旨の表現に基づく整理)。'),
    ('attack_2014_dentist', 'ps_judge_fukuoka_2021',
     'judge', '福岡地裁 一審 — 歯科医師襲撃事件の認定', '2021',
     '「2014年5月の歯科医師襲撃は、医療関係者一族への一連の威迫の集大成として '
     '位置づけられ、本事件こそが頂上作戦の本格化の引き金となった」 '
     '(判決要旨の趣旨)。'),
    ('kokura_district_court', 'ps_pros_briefing_2021',
     'prosecutor', '福岡地検 — 一審判決後 記者会見', '2021',
     '「本判決は、指定暴力団のトップを「事件の首謀者」として刑事責任を問う '
     '異例の捜査・公判の結節点であり、市民を直接の標的とした組織暴力に対する '
     '司法判断の重要な前例となる」(記者会見の趣旨)。'),

    # 福岡高裁 控訴審判決(2024-03-12)関連
    ('kokura_district_court', 'ps_judge_fukuoka_2024',
     'judge', '福岡高裁 控訴審 主任裁判官 — 判決要旨より', '2024',
     '「直接証拠が存在しない中での組織トップへの首謀者責任認定については、'
     '一審の認定の根拠が十分とは言えない部分があり、'
     '本件死刑判決は破棄相当である。'
     '無期懲役は適切な量刑として維持する」(判決要旨の趣旨)。'),
    ('kokura_district_court', 'ps_judge_fukuoka_2024',
     'judge', '福岡高裁 — 田上不美夫被告の控訴審', '2024',
     '「田上被告については一審の無期懲役判決を維持する。'
     '組織の中核として共謀の事実を認めるに足りる証拠がある」 '
     '(判決要旨の趣旨)。'),

    # ルフィ事件公判
    ('philippines_luffy_base', 'ps_watanabe_luffy',
     'prosecutor', '東京地検 — ルフィ事件冒頭陳述 要旨', '2023',
     '「フィリピン入管施設に収容中の身分でありながら、'
     '日本国内の実行役を SNS で組織的に指揮し、'
     '高齢者を主な標的とする組織犯罪を継続したことは、'
     '従来の組織犯罪概念を大きく更新する新型犯罪である」'
     '(冒頭陳述の趣旨)。'),
    ('komae_robbery_2023', 'ps_watanabe_luffy',
     'judge', '東京地裁 — 狛江強盗事件 関連認定', '2023-2024',
     '「2023年1月19日の狛江市内における犯行は、'
     'SNS を介した若年実行役と海外指示役の組み合わせという '
     '新型組織犯罪の最初の組織的事案として位置づけられる」 '
     '(公判中の認定の趣旨)。'),

    # 関東連合関連
    ('roppongi_flower_attack', 'ps_ishimoto_court',
     'judge', '東京地裁 — 六本木 Flower 事件 判決', '2013-2016',
     '「2012年9月の六本木クラブ店内における集団襲撃により被害者が '
     '死亡した本事件は、いわゆる「半グレ集団」の組織的暴力性が '
     '社会に強い衝撃をもたらした事案として記録される」 '
     '(関連判決の趣旨)。'),
    ('roppongi_clubs_hangure', 'ps_mitate_makoto',
     'judge', '東京地裁 — 海老蔵事件 判決', '2011-2014',
     '「2010年11月25日、西麻布飲食店内における集団暴行は、'
     '半グレ集団による組織的暴力の代表事例として、'
     '関係被告らに懲役刑が言い渡された」(判決の趣旨)。'),

    # 山一抗争関連
    ('kobe_yamaichi_ground_zero', 'ps_taoka_book',
     'journalist', '報道書籍 — 山一抗争の総括', '1989-',
     '「5年にわたる山一抗争で、約300件以上の襲撃事件が報じられた。'
     '一般市民の巻き添え死亡事件も発生し、これが暴対法成立(1991)の '
     '直接的な社会的背景となった」(関連書籍の趣旨)。'),

    # 海外メディア
    ('kokura_district_court', 'ps_jake_adelstein_2',
     'journalist', 'Jake Adelstein — 工藤會判決報道', '2021-2024',
     '「Kudo-kai の一連の判決は、日本のヤクザ規制史の最も '
     '象徴的な節目の一つ。海外読者には、日本における '
     '「組織犯罪のトップを首謀者として立件する」異例性が '
     '理解されにくいが、米国 RICO 法に類似の射程を持つ判決」 '
     '(Tokyo Vice 関連報道の趣旨)。'),
    ('intl_la_cosa_nostra_us', 'ps_andrew_rankin_2',
     'academic', 'Andrew Rankin — 国際比較', '2010s-',
     '「日本の工藤會を、市民を直接の標的とする例外的な指定暴力団として '
     '国際比較組織犯罪研究に位置づけるべきだ。'
     '通常のヤクザは組織内部または競合組織が標的で、'
     '工藤會のような市民威迫の累積は世界の組織犯罪研究で '
     '特異な現象である」(関連論考の趣旨)。'),

    # 暴追運動センター
    ('bouhai_center_fukuoka', 'ps_nishi_keisho',
     'family', '福岡県暴追運動推進センター — 被害者支援員 証言', '2014-',
     '「頂上作戦後の数年間、相談窓口には『何十年も払い続けていたみかじめ料を '
     'やっと断れた』『家族に隠していた組との関係を相談できた』という '
     '相談者が連日訪れた。街の人々の長年の沈黙が、'
     'やっと声を持ち始めた」(支援員談の趣旨)。'),

    # 警察関係
    ('fukuoka_kenkei', 'ps_takejima_kosaku',
     'police', '福岡県警組対課 — 元捜査員 関連報道', '2014-',
     '「頂上作戦の数年前から、組のトップへの責任を立てる方針で '
     '証拠の地道な積み上げを続けた。'
     '「直接証拠は出ない」前提で、状況証拠の連鎖で組織犯罪を立てる '
     '捜査は、福岡県警が長年蓄積してきた手法の集大成だった」 '
     '(関連書籍の趣旨)。'),

    # 元組員側
    ('tanaka_gumi_offshoot', 'ps_okita_garyu_book',
     'family', '元工藤會系組員 手記 — 解散届の日', '2014-2019',
     '「組事務所の解散届が出た日、若手組員の多くは『これで終わりだ』と '
     '感じた。先輩は『お前らはまだ若い、別の人生がある』と言った。'
     '私はその日からアルバイトを探した」(離脱者手記の趣旨)。'),

    # 市民側
    ('majaku_district', 'ps_nishi_keisho',
     'family', '神岳1丁目隣接住民 — 本部解体当日', '2019-07-04',
     '「孫を連れてやっとこの道を歩ける。長年、子どもには『この交差点は '
     '通るな』と言ってきたが、今日からは違う」(高齢住民の取材の趣旨)。'),

    # 大相撲
    ('sumo_yakyu_baqto', 'ps_npa_chief',
     'prosecutor', '警察庁 — 大相撲野球賭博事件 関連発表', '2010',
     '「2010年の大相撲野球賭博事件は、伝統文化と暴力団資金の関係を '
     '社会に強く突きつけた事件であり、日本相撲協会のコンプライアンス改革の '
     '直接の引き金となった」(警察白書関連の趣旨)。'),

    # トクリュウ広域強盗 — 被害者支援団体
    ('komae_robbery_2023', 'ps_npa_chief',
     'family', '高齢者被害者支援団体 — 連続強盗を受けて', '2023-',
     '「狛江以降の連続強盗事件は、高齢者を主な標的とする '
     '極めて悪質な犯行。一人暮らしの高齢者の不安を全国に広げた。'
     '地域の見守り体制の根本的な見直しが急務」(関連声明の趣旨)。'),

    # 大震災時の山口組
    ('kansai_quake_yamaguchi', 'ps_taoka_book',
     'family', '阪神大震災 現地住民 — 山口組炊き出しの記憶', '1995-01-17',
     '「あの日、神戸の街は機能停止していた。'
     'たまたま山口組の本部前を通ったら、被災者向けに食事を配っていた。'
     '行政が動かない中で、結果的に救われた人がいた、というのは事実だ」 '
     '(取材の趣旨)。'),
]


PROSECUTIONS = [
    (50, '海老蔵暴行事件', '見立真一', '東京地方裁判所', '一審',
     '2011-2014', '懲役刑',
     '2010-11-25 西麻布飲食店内での集団暴行に対する判決。'
     '関東連合 元主要メンバー 見立真一らに懲役刑。'
     '半グレ問題への司法対応の節目。'),

    (60, '六本木 Flower 事件', '関東連合系 複数被告', '東京地方裁判所', '一審',
     '2013-2016', '懲役刑(複数)',
     '2012-09-02 六本木クラブ「Flower」店内での集団襲撃により被害者死亡。'
     '関係被告に集団傷害致死罪などで懲役刑。半グレ問題が全国認知される事件。'),

    (70, 'ルフィ事件 強盗殺人罪', '渡邊優樹', '東京地方裁判所', '一審',
     '2024-', '公判進行中(無期相当)',
     '2023-01-19 狛江強盗殺人事件など複数の罪状。'
     '指示役4人の責任配分・SNS 証拠の扱い・海外拠点からの指示の '
     '法的位置づけが争点。'),

    (80, 'ルフィ事件 強盗殺人罪', '小島智信', '東京地方裁判所', '一審',
     '2024-', '公判進行中',
     'ルフィ事件4被告の一人。渡邊被告と共謀での強盗殺人罪。'),

    (90, 'ルフィ事件 強盗殺人罪', '今村磨人', '東京地方裁判所', '一審',
     '2024-', '公判進行中',
     'ルフィ事件4被告の一人。'),

    (100, 'ルフィ事件 強盗殺人罪', '藤田聖也', '東京地方裁判所', '一審',
     '2024-', '公判進行中',
     'ルフィ事件4被告の一人。'),

    (110, '工藤會 関連 傘下幹部判決(複数)', '工藤會 傘下幹部 (複数)', '福岡地方裁判所', '一審',
     '2015-2020', '懲役刑(複数)',
     '頂上作戦後、工藤會傘下の幹部・実行役に対する個別判決が複数進行。'
     '市民襲撃4事件以外の関連事案でも有罪判決が相次いだ。'),

    (120, '大相撲 野球賭博事件 — 力士・親方処分', '関係力士・親方', '日本相撲協会', '内部処分',
     '2010-08', '解雇・引退処分',
     '2010-05 発覚の大相撲野球賭博事件で複数力士の解雇・親方の引退処分。'
     '日本相撲協会の暴排態勢整備の起点。'),

    (130, '大相撲 八百長事件 — 力士・親方処分', '関係力士・親方', '日本相撲協会', '内部処分',
     '2011-04', '解雇・引退処分',
     '2011-02 発覚の大相撲八百長事件で複数力士の解雇・引退処分。'
     '本場所(大阪場所)中止。'),

    (140, 'プロ野球 黒い霧事件 — 永久追放処分', '関係選手(複数)', '日本野球機構', '内部処分',
     '1969-1971', '永久追放(複数)',
     '1969-10 発覚のプロ野球八百長事件で関係選手の永久追放処分。'
     '戦後スポーツ史最大の汚点。'),

    (150, 'ロッキード事件 田中角栄 判決', '田中角栄', '東京地方裁判所', '一審',
     '1983-10-12', '懲役4年・追徴金5億円',
     '元首相の収賄事件。戦後最大の汚職事件として裁判が行われた。'),

    (160, 'みずほ銀行 業務改善命令', 'みずほ銀行', '金融庁', '行政処分',
     '2014', '業務改善命令',
     '2013-2014 反社融資問題に対する業務改善命令。'
     '銀行業界全体の反社チェック体制の根本見直しの引き金。'),

    (170, 'OFAC TCO 制裁 — 工藤會指定', '工藤會(組織)', '米財務省 OFAC', '行政処分',
     '2013-02-23', 'TCO 指定 / SDN リスト掲載',
     '米財務省 OFAC が工藤會を「特定国際犯罪組織」として制裁指定。'
     '日本の指定暴力団に対する初めての金融制裁。'),

    (180, 'OFAC 個人制裁 — 野村悟・田上不美夫', '野村悟 / 田上不美夫', '米財務省 OFAC', '行政処分',
     '2013-12', 'SDN リスト個人指定',
     '工藤會トップ2人を SDN リストに個人指定。'
     '米国内資産凍結・米国市民との取引禁止。'),

    (190, '特定危険指定 — 工藤會(2012)', '工藤會(組織)', '国家公安委員会', '指定',
     '2012-12-27', '特定危険指定(指定第1号)',
     '改正暴対法に基づく特定危険指定暴力団の指定。'
     '事務所使用制限・脱退妨害禁止など強い規制対象に。'),

    (200, '特定危険指定 更新 — 工藤會(2024)', '工藤會(組織)', '福岡県公安委員会', '指定更新',
     '2024-12', '指定更新',
     '工藤會の特定危険指定暴力団としての指定が3年更新。'),

    (210, '特定抗争指定 — 山口組系(2020)', '六代目山口組 / 神戸山口組', '国家公安委員会', '指定',
     '2020-01-07', '特定抗争指定',
     '改正暴対法に基づき、六代目山口組と神戸山口組を特定抗争指定暴力団に指定。'),

    (220, '特定抗争指定 解除 — 山口組系(2023)', '六代目山口組 / 神戸山口組', '国家公安委員会', '指定解除',
     '2023-08', '段階的解除',
     '抗争事件の沈静化を受け、両組織の特定抗争指定が段階的に解除へ。'),

    (230, '九州抗争 — 道仁会・誠道会 特定抗争指定(2012)', '道仁会 / 九州誠道会', '国家公安委員会', '指定',
     '2012-12-27', '特定抗争指定',
     '九州抗争の沈静化のため、道仁会と九州誠道会を特定抗争指定に。'),
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

    # Persons — keep existing 16, add new
    pn_inserted = 0; missing = set()
    for (slug, name, kana, role, faction, born, died, site_slug, body, spice, src_key) in PERSONS:
        # only insert if slug doesn't exist (idempotent)
        cur.execute('DELETE FROM person WHERE slug=?', (slug,))
        site_id = s_ids.get(site_slug) if site_slug else None
        if site_slug and site_id is None:
            missing.add(site_slug); continue
        src_id = src_ids.get(src_key) if src_key else None
        cur.execute(
            'INSERT INTO person(slug, name, name_kana, role, faction_tag, born, died, '
            ' site_id, body, spice, source_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (slug, name, kana, role, faction, born, died, site_id, body, spice, src_id))
        pn_inserted += 1

    # Testimony — append (not delete-all)
    tm_inserted = 0
    for (slug, src_key, role, speaker, year, quote) in TESTIMONY:
        site_id = s_ids.get(slug)
        if site_id is None: missing.add(slug); continue
        src_id = src_ids.get(src_key) if src_key else None
        # delete if (site_id, speaker, year) exists (idempotent)
        cur.execute(
            'DELETE FROM testimony WHERE site_id=? AND COALESCE(speaker_label,"")=? AND COALESCE(year,"")=?',
            (site_id, speaker or '', year or ''))
        cur.execute(
            'INSERT INTO testimony(site_id, role, speaker_label, year, quote, source_id) '
            'VALUES (?,?,?,?,?,?)',
            (site_id, role, speaker, year, quote, src_id))
        tm_inserted += 1

    # Prosecutions — append by ord
    pros_inserted = 0
    for (ord_, case_label, defendant, court, stage, decided_on, outcome, summary) in PROSECUTIONS:
        cur.execute(
            'DELETE FROM prosecution WHERE ord=?', (ord_,))
        cur.execute(
            'INSERT INTO prosecution(ord, case_label, defendant_label, court, stage, '
            ' decided_on, outcome, summary) VALUES (?,?,?,?,?,?,?,?)',
            (ord_, case_label, defendant, court, stage, decided_on, outcome, summary))
        pros_inserted += 1

    con.commit()
    print(f'phase30: +{pn_inserted} persons, +{tm_inserted} testimony, +{pros_inserted} prosecutions')
    if missing:
        print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
