"""Phase 26: テーマ深掘り — 経済・政治・興行・スポーツ・薬物・戦後初期抗争。

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('th2_kobe_geinosha_book', 'book', '報道書籍 / 朝日新聞',
     '神戸芸能社 設立(1957)と田岡一雄', None, '1957-'),
    ('th2_kodama_book', 'book', '報道書籍',
     '児玉誉士夫 評伝・関連書籍', None, '1980s-'),
    ('th2_lockheed_news', 'news', '朝日新聞 / 共同通信',
     'ロッキード事件報道(1976-1983)', None, '1976-1983'),
    ('th2_lockheed_ruling', 'ruling', '東京地方裁判所',
     'ロッキード事件 田中角栄判決(1983)', 'https://www.courts.go.jp/', '1983'),
    ('th2_bubble_jiage', 'news', '朝日新聞 / 毎日新聞 / 日経新聞',
     'バブル期 地上げ問題報道(1985-1991)', None, '1985-1991'),
    ('th2_jusen_problem', 'news', '日経新聞 / 朝日新聞',
     '住専問題 報道(1995-1996)', None, '1995-1996'),
    ('th2_hanshin_quake', 'news', '朝日新聞 / 神戸新聞 / NHK',
     '阪神大震災 山口組支援活動 報道(1995)', None, '1995-01'),
    ('th2_kuroikiri_book', 'book', '近藤唯之 / 報道書籍',
     'プロ野球「黒い霧事件」(1969-1971)関連', None, '1969-1971'),
    ('th2_kuroikiri_news', 'news', '朝日新聞 / 読売新聞',
     '黒い霧事件 各選手処分報道', None, '1969-1971'),
    ('th2_sumo_yakyu_baqto', 'news', '朝日新聞 / 毎日新聞 / NHK',
     '大相撲 野球賭博事件 報道(2010)', None, '2010-05'),
    ('th2_sumo_yaocho', 'news', '朝日新聞 / 毎日新聞 / NHK',
     '大相撲 八百長問題 報道(2011)', None, '2011-02'),
    ('th2_drug_history', 'book', '報道書籍 / 厚生労働省',
     '日本の覚せい剤戦後史', None, '1950s-'),
    ('th2_drug_npa', 'official_release', '警察庁',
     '覚せい剤検挙状況 年次推移', 'https://www.npa.go.jp/', '1990-'),
    ('th2_honda_war_book', 'book', '報道書籍',
     '本多会・山口組抗争(1960年代前半)', None, '1960-1965'),
    ('th2_sangokujin', 'book', '報道書籍 / 戦後ヤクザ史',
     '戦後三国人事件 関連書籍', None, '1946-1950'),
    ('th2_hibari_book', 'book', '報道書籍 / 美空ひばり関連',
     '美空ひばり-田岡一雄関係 関連書籍', None, '1957-1989'),
    ('th2_yakuza_geino_general', 'book', '溝口敦 / 鈴木智彦',
     'ヤクザと芸能界の戦後史', None, '1957-1990s'),
    ('th2_pachinko_industry_yakuza', 'book', '報道書籍',
     'パチンコ業界とヤクザの戦後史', None, '1960s-'),
    ('th2_kabukicho_kingdom', 'book', 'Jake Adelstein / 報道書籍',
     '歌舞伎町 王国史 — 関東連合・住吉会・稲川会の縄張り', None, '1990s-'),
    ('th2_kobeyamaguchi_misora', 'book', '報道書籍',
     '美空ひばり「子分」の盃 関連報道', None, '1980s-'),
]


EVENTS = [
    # ===== 神戸芸能社・芸能とヤクザ =====
    ('kobe_geinosha', 'th2_kobe_geinosha_book',
     'merger', '1957',
     '神戸芸能社 設立 — 田岡一雄',
     '1957年、田岡一雄が神戸芸能社を設立。'
     '戦後歌謡界の主要歌手の興行を山口組系で担う体制が確立。'
     'ヤクザと芸能界の戦後の関係を象徴する事業体。',
     None, None, None, '高度成長', '山口組系', 4),

    ('misora_hibari_taoka', 'th2_hibari_book',
     'lore', '1957-1989',
     '美空ひばり-田岡一雄 — 「盃」の関係',
     '美空ひばりは神戸芸能社所属時代(1957-1989)、田岡一雄と「親子の盃」を '
     '交わしたとされる関係。'
     '戦後歌謡界の頂点の歌手とヤクザの組長の特殊な絆として広く知られた。',
     None, None, None, '高度成長', '山口組系', 4),

    ('kobe_geinosha', 'th2_yakuza_geino_general',
     'lore', '1989',
     '神戸芸能社 解散 — 暴排の起点',
     '1989年、田岡一雄の長女(2代目組長の妻)死去をきっかけに、'
     '神戸芸能社は事実上の解散。'
     '芸能界とヤクザの正式な分離が進む起点となり、'
     '後の興行界の暴排運動の素地に。',
     None, None, None, '高度成長', '山口組系', 3),

    ('koshienjo_yakuza', 'th2_yakuza_geino_general',
     'lore', '1960s',
     '甲子園歌謡ショー — 興行の典型',
     '1960年代、甲子園球場での歌謡ショーは神戸芸能社の主要興行。'
     '戦後芸能界の興行とヤクザの関係の典型事例。',
     None, None, None, '高度成長', '山口組系', 2),

    # ===== 政治とヤクザ =====
    ('kodama_yoshio_residence', 'th2_kodama_book',
     'lore', '1950s-1976',
     '児玉誉士夫 — 戦後フィクサー',
     '児玉誉士夫(1911-1984)は戦後の右翼・フィクサー。'
     '政界・財界・ヤクザ社会を結ぶ「裏の中継地点」として戦後昭和に '
     '影響力を持った。1976年ロッキード事件で表面化した戦後ヤクザ史の '
     '重要な背景人物。',
     None, None, None, '高度成長', '司法側', 4),

    ('lockheed_scandal', 'th2_lockheed_news',
     'attack', '1976-02-04',
     'ロッキード事件 — 米上院公聴会で発覚',
     '1976年2月4日、米上院公聴会でロッキード社の航空機販売贈賄が発覚。'
     '田中角栄元首相の関与・児玉誉士夫の代理人ルートが報じられ、'
     '戦後ヤクザと政界の関係が国際的に注目される事件となった。',
     '日本の政治・経済', '贈賄', '社会的衝撃', '高度成長', '司法側', 5),

    ('lockheed_scandal', 'th2_lockheed_ruling',
     'ruling', '1983-10-12',
     'ロッキード事件 田中角栄 一審判決',
     '1983年10月12日、東京地裁が田中角栄元首相に懲役4年・追徴金5億円の '
     '有罪判決。戦後最大の汚職事件として戦後政治史の節目に。'
     '裏社会の関与が司法の場で初めて全国的に議論された事件の一つ。',
     None, None, None, '高度成長', '司法側', 5),

    # ===== バブル期 経済ヤクザ =====
    ('bubble_jiage', 'th2_bubble_jiage',
     'extortion', '1985-1991',
     'バブル期 地上げ — 住民立ち退き暴力',
     '1980年代後半のバブル期、東京都心・地方主要都市の地上げで '
     '住吉会・稲川会・山口組系の関与が広範に報じられた。'
     '住民立ち退き・脅迫・暴力沙汰が社会問題化し、'
     '後の暴対法(1991年成立)の主要背景。',
     '地権者・住民', '脅迫・暴力', '広範な被害', '高度成長', '司法側', 5),

    ('jusen_jutaku', 'th2_jusen_problem',
     'extortion', '1995-1996',
     '住専問題 — ヤクザ系企業への貸付',
     '1995-1996年、住宅金融専門会社(住専)の不良債権処理が国会で議論。'
     '住専の貸付先にヤクザ系企業が含まれていた事実が報じられ、'
     '6850億円の公的資金投入とともに社会問題化した。',
     '国民(公的資金負担)', '迂回融資', '社会的損失', '頂上作戦', '司法側', 4),

    ('kansai_quake_yamaguchi', 'th2_hanshin_quake',
     'lore', '1995-01-17',
     '阪神大震災 — 山口組の支援活動',
     '1995年1月17日の阪神・淡路大震災で、神戸の五代目山口組本部前で '
     '被災者支援(炊き出し・物資配給)を実施。'
     'ヤクザの社会的役割をめぐる議論の重要な事例として、'
     '海外メディアでも繰り返し取り上げられた。',
     None, None, None, '高度成長', '山口組系', 5),

    # ===== スポーツ系 =====
    ('proyakyu_kuroikiri', 'th2_kuroikiri_book',
     'attack', '1969-10',
     'プロ野球「黒い霧事件」発覚',
     '1969年10月、永易将之投手の告発を発端にプロ野球選手の八百長関与が次々と発覚。'
     '指定暴力団との関係が組織的に表面化した戦後スポーツ史最大の事件。'
     '永久追放処分が複数選手に下された。',
     'プロ野球の信頼', '八百長', '選手追放', '高度成長', '司法側', 5),

    ('proyakyu_kuroikiri', 'th2_kuroikiri_news',
     'ruling', '1969-1971',
     '黒い霧 — 関与選手の処分',
     '1969-1971年、関与選手の永久追放・無期出場停止・出場停止などの処分。'
     'プロ野球協約の改正、暴力団排除規定の整備の起点。',
     None, None, None, '高度成長', '司法側', 4),

    ('sumo_yakyu_baqto', 'th2_sumo_yakyu_baqto',
     'attack', '2010-05',
     '大相撲 野球賭博事件 発覚',
     '2010年5月、大相撲力士・親方の野球賭博関与が報道で発覚。'
     '指定暴力団との資金関係が明らかになり、'
     '日本相撲協会は名古屋場所中止寸前まで追い込まれた。',
     '日本相撲協会', '賭博', '社会的衝撃', '頂上作戦', '司法側', 4),

    ('sumo_yakyu_baqto', 'th2_sumo_yakyu_baqto',
     'ruling', '2010-08',
     '大相撲 — 力士・親方の処分',
     '2010年8月、複数力士の解雇・親方の引退処分。'
     '日本相撲協会の暴排態勢が整備され、'
     '指定暴力団との関係遮断が制度化された。',
     None, None, None, '頂上作戦', '司法側', 3),

    ('sumo_yaocho_2011', 'th2_sumo_yaocho',
     'attack', '2011-02',
     '大相撲 八百長問題 発覚',
     '2011年2月、メール記録から大相撲の八百長関与が報道で発覚。'
     '前年の野球賭博事件と続き、相撲協会の暴排態勢の整備が加速。'
     '本場所中止、複数力士の処分。',
     '日本相撲協会', '八百長', '社会的衝撃', '頂上作戦', '司法側', 4),

    # ===== 薬物経済 =====
    ('drug_smuggling_routes', 'th2_drug_history',
     'lore', '1950s-1980s',
     '覚せい剤 戦後史 — 第一・第二次流行',
     '日本の覚せい剤は戦後すぐの第一次流行(1950年代)、'
     '1970年代後半-1980年代の第二次流行を経て継続。'
     '指定暴力団が国内流通を担う構造が確立。'
     '韓国・北朝鮮・中国・東南アジアからの密輸ルートが主軸。',
     None, '密輸・流通', None, '戦後闇市', '司法側', 4),

    ('drug_busts_1990s', 'th2_drug_npa',
     'arrest', '1990s-2024',
     '覚せい剤 大規模摘発(継続)',
     '1990年代以降、海上保安庁・税関・警察による国際密輸摘発が継続。'
     '指定暴力団系の関与が複数の大規模摘発で確認された。'
     '2020年代以降は半グレ・トクリュウ系の関与も報じられた。',
     None, '密輸', '組関係者逮捕', '解体後', '司法側', 3),

    # ===== 戦後初期 =====
    ('honda_kai_war', 'th2_honda_war_book',
     'war', '1960-1965',
     '本多会・山口組抗争',
     '1960年代前半、関西で山口組と本多会の抗争。'
     '田岡一雄時代の山口組が関西統一を進める中で発生した大規模抗争。'
     '一般市民への被害も発生し、後の暴対法の社会的背景の一つに。',
     '組関係者・市民', '拳銃・刃物', '複数死傷', '高度成長', '山口組系', 4),

    ('postwar_sanguokujin', 'th2_sangokujin',
     'attack', '1946-1950',
     '戦後三国人事件 — 関東・関西・九州',
     '戦後直後の闇市における朝鮮人・台湾人など「三国人」集団と '
     '日本人テキ屋系の衝突。関東・関西・九州で複数の事案が報じられた、'
     '戦後ヤクザ史の重要な前史。',
     '組関係者・市民', '集団暴力', '死傷', '戦後闇市', '司法側', 4),

    # ===== 歌舞伎町 / パチンコ =====
    ('tokyo_kabukicho', 'th2_kabukicho_kingdom',
     'lore', '1990s-2010s',
     '歌舞伎町 — 関東主要組織の縄張り交錯',
     '歌舞伎町は住吉会・稲川会・極東会・関東連合(半グレ)など '
     '複数組織の縄張りが交錯する関東最大の歓楽街。'
     'Jake Adelstein のフィールドワークの中心地でもある。',
     None, None, None, '頂上作戦', '司法側', 4),

    ('pachinko_extortion_zone', 'th2_pachinko_industry_yakuza',
     'lore', '1960s-2020s',
     'パチンコ業界 — 戦後史と暴排',
     'パチンコ業界は戦後すぐから指定暴力団系の資金源・縄張りの一部だった。'
     '2007 年の業界暴排条項標準化以降、業界全体の暴排対応が進展。'
     '工藤會のパチンコ脅迫事案はこの全国的構造の地域事例。',
     None, None, None, '解体後', '司法側', 3),

    # ===== その他 =====
    ('kobe_yamaguchi_origin', 'th2_kobeyamaguchi_misora',
     'lore', '1957-1989',
     '美空ひばり「子分」関係 — 戦後芸能の特殊事例',
     '美空ひばりが田岡一雄と交わしたとされる「親子の盃」関係は、'
     '戦後芸能とヤクザの関係を象徴する稀有な事例として議論された。'
     '1989年の田岡長女死去を機に分離が進んだ。',
     None, None, None, '高度成長', '山口組系', 4),
]


LORE = [
    (3500, 'kobe_geinosha', '1957-1989',
     '神戸芸能社 — 戦後芸能の「もう一つの中心」',
     '1957年設立の神戸芸能社は、戦後歌謡界の主要興行を山口組系が担う体制。'
     '美空ひばり・北島三郎・八代亜紀ら戦後を代表する歌手が所属。'
     '1989年解散まで30年余り、戦後芸能の「もう一つの中心」だった。',
     5, '高度成長', '山口組系', 'th2_kobe_geinosha_book'),

    (3510, 'misora_hibari_taoka', '1957-1989',
     '美空ひばり ─ 田岡一雄 「盃」の物語',
     '美空ひばりと田岡一雄の「親子の盃」関係は、戦後芸能とヤクザの '
     '関係を象徴する稀有な事例。芸能界の頂点に立つ歌手と '
     '日本最大の指定暴力団組長の特殊な絆として、関連書籍に繰り返し描かれた。',
     5, '高度成長', '山口組系', 'th2_hibari_book'),

    (3520, 'kodama_yoshio_residence', '1950s-1976',
     '児玉誉士夫 — 「裏の中継地点」',
     '児玉誉士夫は政界・財界・ヤクザ社会を結ぶ「裏の中継地点」として戦後昭和を '
     '生きた。ロッキード事件(1976)で表面化した彼の役割は、'
     '戦後日本の政治とヤクザの関係を国際的に知らせる契機となった。',
     5, '高度成長', '司法側', 'th2_kodama_book'),

    (3530, 'lockheed_scandal', '1976',
     'ロッキード事件 — 日本政治史の転換点',
     'ロッキード事件は戦後日本最大の汚職事件として政治史の転換点となった。'
     '田中角栄元首相の有罪判決(1983)・児玉誉士夫の死去(1984)を経て、'
     '戦後保守政治とヤクザの古典的関係が公的に問われた事件。',
     5, '高度成長', '司法側', 'th2_lockheed_news'),

    (3540, 'bubble_jiage', '1985-1991',
     'バブル地上げ — 「経済ヤクザ」の頂点',
     'バブル期の地上げは「経済ヤクザ」の最盛期。'
     '建物明け渡し・住民立ち退きで指定暴力団の介入が広範に行われた。'
     '1991年の暴対法成立は、この時期の市民被害を直接の背景とする。',
     5, '高度成長', '司法側', 'th2_bubble_jiage'),

    (3550, 'kansai_quake_yamaguchi', '1995-01-17',
     '阪神大震災 — 山口組の炊き出しの絵',
     '阪神大震災当日、五代目山口組本部前で炊き出しが行われた絵は、'
     '海外メディアにも広く配信された。'
     '「公的機関が機能停止した時に裏社会が前に出る」構図として、'
     'ヤクザの社会的役割をめぐる議論の重要な参照点となった。',
     5, '高度成長', '山口組系', 'th2_hanshin_quake'),

    (3560, 'proyakyu_kuroikiri', '1969-1971',
     '黒い霧事件 — 戦後スポーツ史の汚点',
     '黒い霧事件は戦後プロ野球史の最大の汚点。'
     '永易将之の告発に始まる連鎖は複数選手の永久追放につながり、'
     '指定暴力団とプロスポーツの関係を全国的に表面化させた事件。',
     5, '高度成長', '司法側', 'th2_kuroikiri_book'),

    (3570, 'sumo_yakyu_baqto', '2010-05',
     '大相撲野球賭博 — 名古屋場所中止寸前',
     '2010年5月の野球賭博問題で、日本相撲協会は7月の名古屋場所中止を '
     '真剣に検討した。NHK の中継中止という前代未聞の事態。'
     '工藤會頂上作戦の数年前の戦後スポーツ史の節目。',
     5, '頂上作戦', '司法側', 'th2_sumo_yakyu_baqto'),

    (3580, 'sumo_yaocho_2011', '2011-02',
     '大相撲八百長 — メール記録の衝撃',
     '2011年2月の八百長問題はメール記録という現代的証拠で発覚。'
     '前年の野球賭博と続き、相撲協会の暴排・コンプライアンス態勢が '
     '急速に整備された連続事件。',
     4, '頂上作戦', '司法側', 'th2_sumo_yaocho'),

    (3590, 'drug_smuggling_routes', '1950s-2024',
     '覚せい剤 70年 — 流通主体の変遷',
     '日本の覚せい剤流通は戦後70年で主体が変遷。'
     '戦後初期は地場テキ屋系、高度成長期は指定暴力団、'
     '2020年代以降は半グレ・トクリュウ系の独立流通も。'
     '組織犯罪の流動化を象徴する事例。',
     4, '解体後', '司法側', 'th2_drug_history'),

    (3600, 'honda_kai_war', '1960-1965',
     '本多会抗争 — 戦後関西統一の決着',
     '本多会・山口組抗争は田岡一雄時代の山口組による関西統一の決着戦。'
     'この後の山口組全国組織化の足場となった。'
     '戦後ヤクザ史の組織形成期の重要事件。',
     4, '高度成長', '山口組系', 'th2_honda_war_book'),

    (3610, 'postwar_sanguokujin', '1946-1950',
     '戦後三国人事件 — 闇市の地政学',
     '戦後直後の闇市で発生した「三国人」集団と日本人テキ屋系の衝突は、'
     '戦後ヤクザ史の前史として重要。'
     '関東・関西・九州それぞれで地場勢力の組織化を促した。',
     4, '戦後闇市', '司法側', 'th2_sangokujin'),

    (3620, 'pachinko_extortion_zone', '1960s-2024',
     'パチンコ業界 60年 — 暴排の段階的進展',
     'パチンコ業界の暴排対応は戦後60年で段階的に進展。'
     '2007 業界条項標準化・2011 暴排条例全国整備・2014 工藤會頂上作戦を経て、'
     '指定暴力団との関係遮断がほぼ完了。',
     3, '解体後', '司法側', 'th2_pachinko_industry_yakuza'),

    (3630, 'tokyo_kabukicho', '1990s-2020s',
     '歌舞伎町 — 「縄張り交錯地帯」の継続',
     '歌舞伎町は住吉会・稲川会・極東会・関東連合(半グレ)・トクリュウ など '
     '複数組織が縄張りを共有する関東最大の歓楽街。'
     '工藤會の堺町(単一支配)と対照的な構造が継続している。',
     4, '解体後', '司法側', 'th2_kabukicho_kingdom'),
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
    print(f'phase26_thematic: +{ev_inserted} events, +{lr_inserted} lore')
    if missing: print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
