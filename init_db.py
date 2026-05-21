"""Initialize kokura.db with the base schema and seed core entities.

This script is idempotent and re-runnable. It (re)creates the database file at
kokura.db with the full schema, then seeds the base entities (sites, the
chronicle of the Kudo-kai's organizational lineage, and prosecution skeleton).

Downstream phase scripts (phase4..phase10) populate derived data on top.

Coordinate policy (see README "注意・倫理"):
  - Public landmarks / former buildings (HQ, market, district centroids) get
    specific lat/lon.
  - Attacks on private residences or workplaces get the chome/town centroid
    only, with uncertainty_m reflecting that. We do not encode street numbers
    even when reported, to avoid pointing at victims' addresses.

Run: python init_db.py
"""
from __future__ import annotations
import os, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SCHEMA = """
CREATE TABLE IF NOT EXISTS place (
    id INTEGER PRIMARY KEY,
    name_canonical TEXT NOT NULL,
    admin_country TEXT,
    admin_state TEXT,
    centroid_lat REAL,
    centroid_lon REAL
);

-- A "site" is anything we want to anchor satellite frames, POIs, events,
-- testimony, or narration to. It can be: an organization HQ (former or current),
-- an attack location (chome centroid), a relevant district (entertainment
-- quarter), or a landmark (market, station).
CREATE TABLE IF NOT EXISTS site (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    label TEXT NOT NULL,
    place_id INTEGER REFERENCES place(id),
    rep_lat REAL,
    rep_lon REAL,
    uncertainty_m INTEGER,
    kind TEXT,           -- hq_former / hq_current / attack_site / district / landmark / front / lore_site
    first_seen TEXT,
    last_seen TEXT,
    status TEXT,         -- active / demolished / dispersed / unknown
    notes TEXT,
    era_tag TEXT,        -- 戦後闇市 / 高度成長 / 平成抗争 / 頂上作戦 / 解体後
    faction_tag TEXT     -- 工藤會 / 草野一家系 / 工藤組系 / 田中組系 / 山口組系 / 道仁会系 / 県警側 / 司法側 / 市民側
);

CREATE TABLE IF NOT EXISTS source (
    id INTEGER PRIMARY KEY,
    kind TEXT,           -- news / ruling / police_whitepaper / book / official_release
    outlet TEXT,
    title TEXT,
    url TEXT,
    published_on TEXT,
    captured_at TEXT,
    og_image TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS event (
    id INTEGER PRIMARY KEY,
    kind TEXT,           -- attack / arrest / ruling / dissolution / demolition / designation /
                         -- merger / death / extortion / raid / faction_split / war / lore
    happened_on TEXT,    -- ISO date (YYYY-MM-DD or YYYY-MM or YYYY)
    site_id INTEGER REFERENCES site(id),
    title TEXT,
    summary TEXT,
    victim_role TEXT,    -- e.g. "元漁協理事", "歯科医師", "看護師", "元警察官", "建設業者"
    weapon TEXT,         -- e.g. "拳銃", "刃物", "放火", "脅迫"
    resolution TEXT,     -- e.g. "死亡", "重傷", "無事", "起訴"
    source_id INTEGER REFERENCES source(id),
    era_tag TEXT,
    faction_tag TEXT,
    severity INTEGER     -- 1 (small) .. 5 (history-defining)
);

CREATE TABLE IF NOT EXISTS testimony (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES site(id),
    event_id INTEGER REFERENCES event(id),
    role TEXT,           -- victim / family / prosecutor / judge / police / journalist
    speaker_label TEXT,  -- 役職表記のみ。氏名は記載しない
    year TEXT,
    quote TEXT,
    source_id INTEGER REFERENCES source(id)
);

-- Organizational lineage: a single row per inflection point in the chronicle.
-- ord controls timeline order.
CREATE TABLE IF NOT EXISTS chronicle (
    id INTEGER PRIMARY KEY,
    ord INTEGER,
    year_label TEXT,     -- e.g. "1947", "1987", "2000", "2012", "2014", "2019-07"
    title TEXT,
    body TEXT,
    source_id INTEGER REFERENCES source(id),
    era_tag TEXT,
    faction_tag TEXT
);

-- Colorful / entertainment-leaning anecdotes from public reporting. These get
-- their own card style in the dashboard so they don't pretend to be primary
-- court record. Each lore row anchors to a site (or NULL = floating) and a
-- chronological year.
CREATE TABLE IF NOT EXISTS lore (
    id INTEGER PRIMARY KEY,
    ord INTEGER,
    site_id INTEGER REFERENCES site(id),
    year_label TEXT,
    title TEXT,
    body TEXT,
    spice INTEGER,       -- 1 (mild) .. 5 (legendary)
    era_tag TEXT,
    faction_tag TEXT,
    source_id INTEGER REFERENCES source(id)
);

-- Major prosecutions and their procedural history.
CREATE TABLE IF NOT EXISTS prosecution (
    id INTEGER PRIMARY KEY,
    ord INTEGER,
    case_label TEXT,     -- e.g. "頂上作戦 4事件統合公判"
    defendant_label TEXT,-- e.g. "野村悟", "田上不美夫"  (公人として公開判決にある被告)
    court TEXT,          -- e.g. "福岡地裁", "福岡高裁", "最高裁"
    stage TEXT,          -- 一審 / 控訴審 / 上告審
    decided_on TEXT,
    outcome TEXT,
    summary TEXT,
    source_id INTEGER REFERENCES source(id)
);

CREATE TABLE IF NOT EXISTS poi (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES site(id),
    lat REAL,
    lon REAL,
    poi_type TEXT,
    name TEXT,
    descr TEXT,
    confidence TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS imagery_release (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES site(id),
    release_num INTEGER,
    release_date TEXT,
    tile_z INTEGER,
    tile_x INTEGER,
    tile_y INTEGER,
    tile_url TEXT,
    tile_sha256 TEXT,
    is_distinct INTEGER
);

CREATE TABLE IF NOT EXISTS image_resource (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES site(id),
    local_path TEXT,
    title TEXT,
    caption TEXT,
    credit TEXT,
    license TEXT,
    source_url TEXT
);

CREATE TABLE IF NOT EXISTS event_image (
    id INTEGER PRIMARY KEY,
    event_id INTEGER REFERENCES event(id),
    image_url TEXT,
    captured_at TEXT
);

CREATE TABLE IF NOT EXISTS narration (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES site(id),
    ord INTEGER,
    title TEXT,
    body TEXT
);

CREATE TABLE IF NOT EXISTS era_caption (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES site(id),
    year INTEGER,
    caption TEXT
);

CREATE TABLE IF NOT EXISTS life_snippet (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES site(id),
    ord INTEGER,
    topic TEXT,
    text TEXT,
    source_label TEXT,
    source_url TEXT
);

CREATE TABLE IF NOT EXISTS local_spot (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES site(id),
    lat REAL,
    lon REAL,
    category TEXT,
    kind TEXT,
    name TEXT
);

CREATE TABLE IF NOT EXISTS danger_detail (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES site(id),
    category TEXT,       -- weapon / target / pattern / impact
    text TEXT,
    source_url TEXT
);

-- Publicly-named individuals: deceased historical figures, defendants in
-- published rulings, authors of cited works, public-record officials. We do
-- NOT include living rank-and-file members or victims by name.
CREATE TABLE IF NOT EXISTS person (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    name_kana TEXT,
    role TEXT,           -- founder / boss / underboss / defendant / judge /
                         -- prosecutor / police_chief / author / academic / journalist /
                         -- film_maker / political_figure
    faction_tag TEXT,    -- 工藤會 / 草野一家系 / 工藤組系 / 県警側 / 司法側 / 著作者
    born TEXT,
    died TEXT,
    site_id INTEGER REFERENCES site(id),   -- anchor (HQ for org, court for judges, etc.)
    body TEXT,           -- short bio drawn from public reporting
    spice INTEGER,
    source_id INTEGER REFERENCES source(id)
);

-- Year-keyed crime stats from police white papers and 暴追運動推進センター
-- annual reports. metric is one of:
--   members       — 工藤會構成員・準構成員推定数
--   members_full  — 構成員のみ
--   handguns      — 北九州/福岡における年間押収拳銃数
--   advice_cases  — 暴排相談件数(福岡県)
--   warnings      — 中止命令・再発防止命令件数
--   defectors     — 離脱者支援件数(福岡県)
CREATE TABLE IF NOT EXISTS crime_stat (
    id INTEGER PRIMARY KEY,
    metric TEXT,
    year INTEGER,
    value REAL,
    unit TEXT,
    notes TEXT,
    source_id INTEGER REFERENCES source(id),
    UNIQUE(metric, year)
);

-- Organizational genealogy edges. A row says "child organisation depends on
-- parent organisation in the relation `kind`" (umbrella / direct_subord /
-- offshoot_from / merged_into / dissolved_into).
CREATE TABLE IF NOT EXISTS org_tree (
    id INTEGER PRIMARY KEY,
    child TEXT NOT NULL,         -- short name
    parent TEXT,                 -- short name or NULL for root
    kind TEXT,                   -- umbrella / direct_subord / offshoot_from / merged_into / dissolved_into
    started TEXT,
    ended TEXT,
    notes TEXT,
    faction_tag TEXT
);
"""


# ---------- Seed data ----------
# Coordinates: only landmarks / former public buildings get specific lat/lon.
# Attack sites use the chome centroid (uncertainty_m ~ 200) and avoid the
# victim's exact address.

PLACES = [
    # id, name, country, state, lat, lon
    (1, '北九州市小倉北区',     'JP', '福岡県', 33.8852, 130.8800),
    (2, '北九州市若松区',       'JP', '福岡県', 33.9008, 130.8074),
    (3, '北九州市門司区',       'JP', '福岡県', 33.9447, 130.9628),
    (4, '芦屋町',               'JP', '福岡県', 33.8978, 130.6611),
    (5, '田川市',               'JP', '福岡県', 33.6444, 130.8053),
    (6, '中津市',               'JP', '大分県', 33.5985, 131.1883),
    (7, '北九州市小倉南区',     'JP', '福岡県', 33.8430, 130.8807),
    (8, '北九州市八幡西区',     'JP', '福岡県', 33.8638, 130.7195),
    (9, '北九州市八幡東区',     'JP', '福岡県', 33.8678, 130.8044),
    (10, '北九州市戸畑区',      'JP', '福岡県', 33.8919, 130.8333),
    (11, '久留米市',            'JP', '福岡県', 33.3192, 130.5083),
    (12, '直方市',              'JP', '福岡県', 33.7444, 130.7261),
    (13, '苅田町',              'JP', '福岡県', 33.7794, 130.9694),
    (14, '宗像市',              'JP', '福岡県', 33.8050, 130.5586),
    (15, '春日市',              'JP', '福岡県', 33.5347, 130.4708),
    (16, '行橋市',              'JP', '福岡県', 33.7283, 130.9772),
    (17, '大牟田市',            'JP', '福岡県', 33.0306, 130.4458),
]


SITES = [
    # slug, label, place_id, lat, lon, unc_m, kind, first_seen, last_seen, status, notes,
    #   era_tag, faction_tag
    ('kudokai_hq_kandake',
     '工藤會本部跡(神岳)',
     1, 33.8886, 130.8800, 30,
     'hq_former', '1987', '2019-08', 'demolished',
     '北九州市小倉北区神岳1丁目。2019年7月解体着手、同8月までに更地化。'
     '跡地はその後競売・売却。座標は判決および主要報道で公表された所在地に基づく。',
     '平成抗争', '工藤會'),
    ('tanga_market',
     '旦過市場',
     1, 33.8839, 130.8810, 50,
     'landmark', '1955', None, 'active',
     '小倉北区魚町。2022-04-19 と 2022-08-10 に二度の大規模火災(原因は捜査中・別件)。'
     '工藤會本部からの徒歩圏で、街の現況コンテキストとして本マップに収録。',
     '解体後', '市民側'),
    ('uomachi_arcade',
     '魚町銀天街',
     1, 33.8848, 130.8788, 50,
     'district', '1951', None, 'active',
     '日本初のアーケード商店街(1951)。小倉中心市街の動脈。',
     '戦後闇市', '市民側'),
    ('sakaimachi_quarter',
     '堺町歓楽街',
     1, 33.8852, 130.8800, 100,
     'district', None, None, 'active',
     '小倉北区堺町1〜2丁目。九州有数の歓楽街。長年、工藤會傘下のみかじめ料徴収・'
     'トラブル介入の温床と報じられてきたエリア。',
     '高度成長', '工藤會'),
    ('kokura_station',
     '小倉駅',
     1, 33.8866, 130.8826, 30,
     'landmark', '1891', None, 'active',
     '北九州市の中心ターミナル。',
     '高度成長', '市民側'),
    # Attack sites: chome centroid only.
    ('attack_1998_ashiya_fisheries',
     '1998年 元漁協理事射殺地点(芦屋町)',
     4, 33.8978, 130.6611, 400,
     'attack_site', '1998-02-18', '1998-02-18', 'historical',
     '町中心の概略座標。報道・判決による事件発生地は芦屋町内。'
     '被害者の番地は記載しない。',
     '平成抗争', '工藤會'),
    ('attack_2012_ex_officer',
     '2012年 元警察官襲撃地点(小倉北区)',
     1, 33.8800, 130.8750, 600,
     'attack_site', '2012-04-19', '2012-04-19', 'historical',
     '小倉北区内。町丁目重心に丸めた概略座標。被害者の住所は記載しない。',
     '平成抗争', '工藤會'),
    ('attack_2013_nurse',
     '2013年 看護師女性襲撃地点(小倉北区)',
     1, 33.8870, 130.8720, 600,
     'attack_site', '2013-01-28', '2013-01-28', 'historical',
     '小倉北区内。町丁目重心の概略座標。被害者は当時の歯科医師の親族と報道。',
     '平成抗争', '工藤會'),
    ('attack_2014_dentist',
     '2014年 歯科医師襲撃地点(小倉北区中井)',
     1, 33.8830, 130.8700, 600,
     'attack_site', '2014-05-26', '2014-05-26', 'historical',
     '小倉北区中井エリアの概略座標。被害者の番地は記載しない。',
     '平成抗争', '工藤會'),

    # ===== 新規 — エンタメ層 / 中小事件 / 派閥 =====
    ('kudokai_hq_kandake_signboard',
     '神岳「金看板」事件現場(本部跡近接)',
     1, 33.8888, 130.8802, 30,
     'lore_site', '1987', '2019', 'demolished',
     '工藤會本部の正面に長年掲げられていた金属製看板。'
     '解体時に「指定暴力団の看板を撤去する」象徴的な絵として全国に流れた。',
     '頂上作戦', '工藤會'),

    ('kokura_district_court',
     '福岡地方裁判所小倉支部',
     1, 33.8861, 130.8762, 20,
     'landmark', None, None, 'active',
     '小倉北区金田。工藤會関連の多数の公判が開かれた地裁支部。'
     '判決言渡の度に報道陣が並ぶ。',
     '頂上作戦', '司法側'),

    ('fukuoka_kenkei',
     '福岡県警察 北九州地区本部',
     1, 33.8845, 130.8772, 30,
     'landmark', None, None, 'active',
     '小倉北区中央町。県警組織犯罪対策課・暴力団対策担当が拠点とする。'
     '2014年頂上作戦の指揮所もここから。',
     '頂上作戦', '県警側'),

    ('ogura_keisatsu',
     '小倉北警察署',
     1, 33.8879, 130.8810, 25,
     'landmark', None, None, 'active',
     '神岳の工藤會本部からわずか200mの距離にあった。'
     '戦後北九州の独特な地域構造を象徴する近接配置。',
     '高度成長', '県警側'),

    ('heisei_shinten_chi',
     '平成新天地(2003年襲撃事件現場)',
     1, 33.8860, 130.8810, 200,
     'attack_site', '2003', '2003', 'historical',
     '小倉北区平和通り周辺の歓楽街エリア。2003年に発生した一連の襲撃・脅迫事件が '
     '「平成新天地事件」として報道された。後の頂上作戦への伏線とされる。',
     '平成抗争', '工藤會'),

    ('construction_extortion_kitakyushu',
     '建設業者一連の襲撃(北九州市内・複数地点)',
     1, 33.8780, 130.8790, 800,
     'attack_site', '2003', '2014', 'historical',
     '工藤會傘下による建設業者・ゼネコン・解体業者への一連のみかじめ要求と襲撃。'
     '報道された個別事件は十数件に上る。地点は市内複数で、概念的代表点として表示。',
     '平成抗争', '工藤會'),

    ('snack_kuyakushotsuki',
     '小倉北区スナック・キャバクラ一帯(みかじめ料事案)',
     1, 33.8856, 130.8805, 250,
     'attack_site', '2000', '2014', 'historical',
     '堺町・京町周辺のスナック・キャバクラに対するみかじめ料徴収事案。'
     '頂上作戦着手前後、暴排ステッカー導入・通報窓口整備が進んだエリア。',
     '平成抗争', '工藤會'),

    ('kurume_dojinkai_hq',
     '道仁会系拠点(久留米市)',
     1, 33.3192, 130.5083, 600,
     'lore_site', '1971', None, 'active',
     '久留米市を拠点とする道仁会。2006-2013年の道仁会・九州誠道会(後の浪川会)の '
     '抗争は北九州市にも飛び火し、工藤會の縄張りに緊張をもたらした。',
     '平成抗争', '道仁会系'),

    ('yamaguchigumi_kyushu_entry',
     '山口組九州進出ライン(関門・1980s)',
     3, 33.9447, 130.9628, 800,
     'lore_site', '1980', '1995', 'historical',
     '1980年代に山口組系列が九州進出を強め、北九州の地場組織との緊張が高まった。'
     '工藤會(当時 工藤連合草野一家)はこれに防衛側で対峙し、後の連合体強化につながった。',
     '高度成長', '山口組系'),

    ('tanaka_gumi_offshoot',
     '田中組系離脱・分裂エリア(小倉北区)',
     1, 33.8800, 130.8810, 400,
     'lore_site', '2014', None, 'dispersed',
     '工藤會傘下の主要組「田中組」は頂上作戦以降、内部分裂と組員流出を経験。'
     '報道された組事務所撤去・関連幹部の引退が続いた。',
     '頂上作戦', '田中組系'),

    ('kusano_ikka_origin_kokura',
     '草野一家発祥地(戦後闇市・小倉)',
     1, 33.8830, 130.8800, 500,
     'lore_site', '1947', '1953', 'historical',
     '初代総長 草野高明が戦後の小倉でテキ屋系から草野一家を結成。'
     '小倉駅・旦過市場の闇市文化と地続きの出自として知られる。'
     '正確な発祥地番地は不明、概念的代表点。',
     '戦後闇市', '草野一家系'),

    ('kudogumi_nakatsu_origin',
     '工藤組発祥地(中津市)',
     6, 33.5985, 131.1883, 800,
     'lore_site', '1953', '1987', 'historical',
     '初代組長 工藤玄治が大分県中津市で工藤組を結成。'
     '後年、北九州の草野一家との連携、そして1987年の工藤連合草野一家成立へ。',
     '戦後闇市', '工藤組系'),

    ('security_guard_attack',
     '警備員襲撃事件発生地概略(小倉北区)',
     1, 33.8860, 130.8790, 400,
     'attack_site', '2010', '2014', 'historical',
     '建設現場警備員・施設警備員への襲撃が複数報道された。'
     '組による「威迫の対象を市民に広げる」局面の典型事例。',
     '平成抗争', '工藤會'),

    ('ex_member_retaliation',
     '脱退者報復事件発生地概略(小倉北区)',
     1, 33.8810, 130.8770, 500,
     'attack_site', '2003', '2014', 'historical',
     '脱退組員への報復襲撃事件が複数報道された。'
     '改正暴対法の「脱退妨害禁止」規制対象指定の重要な背景となった事案群。',
     '平成抗争', '工藤會'),

    ('pachinko_extortion_zone',
     'パチンコ店脅迫事案ライン(北九州市)',
     1, 33.8830, 130.8810, 500,
     'attack_site', '2000', '2014', 'historical',
     '北九州市内パチンコ店・遊技場への脅迫・みかじめ要求事案が複数報道された。'
     '頂上作戦以降、業界団体による暴排相談窓口整備が進んだ。',
     '平成抗争', '工藤會'),

    # ===== 多様ソース対応の新拠点 =====
    ('ofac_treasury_designation',
     '米財務省 OFAC 制裁指定ライン(2013-02-23)',
     1, 33.8884, 130.8798, 60,
     'lore_site', '2013-02-23', None, 'active',
     '2013年2月23日、米財務省 OFAC が工藤會を「特定国際犯罪組織(TCO)」として制裁指定。'
     '日本の指定暴力団としては初の事例。野村悟・田上不美夫は個人としても SDN リストに掲載。'
     '本マップでは本部跡の隣接点を象徴的代表点として表示。',
     '平成抗争', '司法側'),

    ('kokkai_diet_tokyo',
     '国会(暴対法改正審議)',
     1, 35.6758, 139.7447, 0,
     'lore_site', '1991', '2024', 'active',
     '東京・永田町。1991年の暴対法成立以降、複数回にわたる改正が国会で審議された。'
     '2012年改正で「特定危険指定」が導入され、工藤會が第1号指定となった。',
     '平成抗争', '司法側'),

    ('bouhai_center_fukuoka',
     '福岡県暴追運動推進センター',
     1, 33.5879, 130.4172, 50,
     'landmark', None, None, 'active',
     '福岡市内。事業者向け暴排相談・離脱者支援・暴追研修を担う民間中核機関。'
     '頂上作戦以降、相談件数は段階的に変化し、業界別の事例集が公開されている。',
     '解体後', '市民側'),

    ('fukuoka_pref_assembly',
     '福岡県議会(暴排条例議論)',
     1, 33.5897, 130.4216, 30,
     'landmark', None, None, 'active',
     '福岡市中央区。2010年の暴力団排除条例制定以降、関連改正・事業者向け規制の '
     '議論が継続。議事録には工藤會関連の答弁が多数残る。',
     '平成抗争', '司法側'),

    ('kitakyushu_city_council',
     '北九州市議会',
     1, 33.8854, 130.8755, 30,
     'landmark', None, None, 'active',
     '小倉北区。暴排相談センター予算・地域防犯予算・解体跡地問題などが議題に。'
     '頂上作戦以降、暴排関連の議事は安定して質疑が続く。',
     '頂上作戦', '司法側'),

    ('kokuraminami_district',
     '小倉南区(下部組織事務所群)',
     1, 33.8590, 130.8810, 1500,
     'lore_site', '1990s', None, 'historical',
     '小倉南区にも工藤會下部組織の事務所群が散在した。報道書籍では '
     '「小倉北の本部 — 小倉南の傘下事務所」の二層構造として描かれる。',
     '高度成長', '工藤會'),

    ('moji_kanmon_line',
     '門司・関門海峡ライン',
     3, 33.9447, 130.9628, 800,
     'lore_site', '1950s', None, 'active',
     '関門海峡の小倉側ライン。中津 — 門司 — 小倉という工藤組系・草野一家系の '
     '人と物の往来ラインが、戦後ヤクザ研究書籍に繰り返し描かれてきた。',
     '戦後闇市', '工藤組系'),

    ('yawata_iron_works_area',
     '八幡製鉄所周辺(労働者街)',
     9, 33.8553, 130.8052, 800,
     'lore_site', '1950s', None, 'active',
     '八幡製鐵所(現・日本製鉄)周辺の労働者街。戦後の組織犯罪研究で「重工業都市の '
     'ヤクザ文化」として繰り返し言及される。北九州ヤクザ史の経済的背景。',
     '戦後闇市', '市民側'),

    # ===== 細かい町丁目レベル =====
    # 小倉北区(細部)
    ('kyomachi_quarter',
     '京町(歓楽街)',
     1, 33.8855, 130.8820, 100,
     'district', None, None, 'active',
     '小倉北区京町1〜3丁目。堺町と並ぶ歓楽街エリア。'
     'みかじめ料事案・暴排ステッカー普及エピソードの中心地の一つ。',
     '平成抗争', '工藤會'),

    ('muromachi_arcade',
     '室町商店街',
     1, 33.8870, 130.8780, 60,
     'district', '1960s', None, 'active',
     '小倉北区室町。古くからの商店街で、戦後の街の動脈の一つ。'
     '暴排ステッカー普及の初期段階で取り組みが進んだエリア。',
     '高度成長', '市民側'),

    ('sunatsu_business_area',
     '砂津 — 商業・バスターミナル',
     1, 33.8845, 130.8870, 80,
     'district', None, None, 'active',
     '小倉北区砂津。長距離バスターミナル(西鉄高速バス)・ホテル・商業施設が集まる '
     '地域。観光客と地元客の混在エリアで、暴排対応の必要性が継続的に議論された。',
     '頂上作戦', '市民側'),

    ('mihagino_district',
     '三萩野(2012年元警察官襲撃地周辺)',
     1, 33.8775, 130.8830, 400,
     'attack_site', '2012', '2012', 'historical',
     '小倉北区三萩野周辺。2012年元警察官襲撃事件の報道エリアに含まれる。'
     '住宅と商業が混在し、襲撃事件後に防犯講習が地元自治会で行われた。',
     '平成抗争', '工藤會'),

    ('chuocho_center',
     '中央町(県警北九州地区本部一帯)',
     1, 33.8845, 130.8772, 80,
     'district', None, None, 'active',
     '小倉北区中央町。福岡県警北九州地区本部・小倉北警察署のすぐ近接エリア。'
     '行政官庁が並ぶ街区。',
     '頂上作戦', '県警側'),

    ('komemachi_arcade',
     '米町・大手町 ライン',
     1, 33.8852, 130.8755, 100,
     'district', None, None, 'active',
     '小倉北区米町・大手町。小倉駅と中央町を結ぶ動線。'
     '商業ビル・オフィスが集まり、頂上作戦以降の暴排相談窓口設置が進んだ。',
     '頂上作戦', '市民側'),

    ('majaku_district',
     '馬借(神岳本部跡の隣接町)',
     1, 33.8868, 130.8825, 80,
     'district', None, None, 'active',
     '小倉北区馬借。神岳1丁目の工藤會本部跡から徒歩数分。'
     '住宅と小規模事業所が混在し、本部解体当時には住民の取材コメントが '
     '地元紙に多く掲載された。',
     '頂上作戦', '市民側'),

    ('kandake_intersection',
     '神岳交差点(本部跡正面)',
     1, 33.8887, 130.8804, 20,
     'lore_site', '1987', None, 'active',
     '工藤會本部跡の正面交差点。「金看板」を見上げる位置として '
     '報道写真の定番アングルだった場所。',
     '頂上作戦', '工藤會'),

    ('uomachi_kawazoi',
     '魚町・神嶽川沿い(旦過市場北側)',
     1, 33.8842, 130.8807, 50,
     'district', None, None, 'active',
     '小倉北区魚町、神嶽川沿いの細長い街区。'
     '旦過市場の北側に位置し、2022年の大火で大きく失われた。',
     '解体後', '市民側'),

    ('heiwa_dori_street',
     '平和通り(平成新天地事件 報道エリア)',
     1, 33.8862, 130.8810, 200,
     'attack_site', '2003', '2003', 'historical',
     '小倉北区の平和通り周辺。2003年の「平成新天地事件」報道エリアと重なる。'
     '歓楽街と業務街の境界に位置する動線。',
     '平成抗争', '工藤會'),

    # 小倉南区(細部)
    ('kokuraminami_yugawa',
     '小倉南区 湯川(下部組織事務所跡 報道)',
     7, 33.8525, 130.8862, 600,
     'lore_site', '2000s', '2018', 'demolished',
     '小倉南区湯川エリア。報道された傘下組事務所跡の一つ。'
     '頂上作戦以降の撤去ラッシュで更地化が進んだ。',
     '頂上作戦', '田中組系'),

    ('kokuraminami_tokuriki',
     '小倉南区 徳力(住宅街・防犯講習エリア)',
     7, 33.8240, 130.8810, 500,
     'district', None, None, 'active',
     '小倉南区徳力。郊外住宅地で、地域自治会主催の暴排講習が継続的に開催された。',
     '頂上作戦', '市民側'),

    # 若松区
    ('wakamatsu_takatosan',
     '若松区(高塔山周辺・住民連携)',
     2, 33.9008, 130.8074, 500,
     'district', None, None, 'active',
     '若松区高塔山周辺。住宅地と商業地が混在し、'
     '北九州市暴追運動推進会議による地域連携活動の現場の一つ。',
     '解体後', '市民側'),

    # 八幡西区
    ('kurosaki_arcade',
     '黒崎(八幡西区中心市街)',
     8, 33.8638, 130.7195, 100,
     'district', None, None, 'active',
     '八幡西区黒崎。北九州市西部の中心市街地。'
     'JR黒崎駅周辺の商業エリアで、暴排ステッカー普及・暴排講習が定期的に行われた。',
     '頂上作戦', '市民側'),

    ('orio_station_area',
     '折尾(八幡西区・学生街)',
     8, 33.8736, 130.6975, 150,
     'district', None, None, 'active',
     '八幡西区折尾。九州共立大学・産業医科大学などが近い学生街。'
     '飲食店暴排講習の機会が大学側からも提供された。',
     '頂上作戦', '市民側'),

    # 八幡東区
    ('yahatahigashi_kawatamachi',
     '八幡東区(製鐵所労働者街の現代版)',
     9, 33.8678, 130.8044, 400,
     'district', None, None, 'active',
     '八幡東区。日本製鉄(旧八幡製鐵所)関連の住宅・商業エリア。'
     '戦後ヤクザ史で「重工業都市の労働者街」として論じられた地域の現代の姿。',
     '解体後', '市民側'),

    # 門司区
    ('moji_sakaecho',
     '門司区 栄町(港湾労働者街)',
     3, 33.9425, 130.9610, 250,
     'district', None, None, 'active',
     '門司区栄町。門司港旧市街地。港湾労働の歴史と関門ヤクザ史の交点。'
     '関連報道書籍に繰り返し描かれる場所。',
     '戦後闇市', '工藤組系'),

    # 戸畑区
    ('tobata_yomiya',
     '戸畑区(夜宮周辺)',
     10, 33.8919, 130.8333, 400,
     'district', None, None, 'active',
     '戸畑区。新日鉄住金化学関連の街。北九州5市合併前の旧市の一つで、'
     '地域自治会の暴排活動が早い時期から組まれた。',
     '高度成長', '市民側'),

    # 周辺市町村
    ('kurume_bunkagai',
     '久留米市 文化街(道仁会・浪川会の縄張り)',
     11, 33.3245, 130.5085, 300,
     'district', None, None, 'active',
     '久留米市文化街。道仁会・浪川会(旧九州誠道会)の歴史的縄張りに含まれる歓楽街。'
     '九州抗争(2006-2013)期の発砲事件が断続的に報じられた。',
     '平成抗争', '道仁会系'),

    ('omuta_dojin_relation',
     '大牟田市(九州抗争の南端)',
     17, 33.0306, 130.4458, 1000,
     'lore_site', '2006', '2013', 'historical',
     '大牟田市。九州抗争(2006-2013)の余波が南端まで及んだエリア。'
     '関連報道で複数の事案が報じられた。',
     '平成抗争', '道仁会系'),

    ('tagawa_taishu_hq',
     '田川市(太州会本拠)',
     5, 33.6444, 130.8053, 800,
     'lore_site', '1978', None, 'active',
     '田川市。太州会の本拠地。'
     '九州地場ヤクザの代表的縄張りの一つ。'
     '工藤會が小倉北区を、太州会が田川を、と地域分割が成立していた構図が '
     '報道書籍に描かれた。',
     '高度成長', '道仁会系'),

    ('nogata_bouhai_event',
     '直方市(暴排対応事案)',
     12, 33.7444, 130.7261, 600,
     'district', None, None, 'active',
     '直方市。北九州市と田川市の中間に位置し、両地場組織の境界エリア。'
     '事業者向け暴排講習の事例が報じられた。',
     '頂上作戦', '市民側'),

    ('munakata_pref',
     '宗像市(郊外住宅と関連事件)',
     14, 33.8050, 130.5586, 800,
     'district', None, None, 'active',
     '宗像市。北九州都市圏と福岡市都市圏の中間。'
     '関連報道で個別事件が散発的に報じられた。',
     '頂上作戦', '市民側'),

    ('kasuga_fukuhakukai',
     '春日市(福博会関連)',
     15, 33.5347, 130.4708, 500,
     'lore_site', '1990s', None, 'active',
     '春日市。福岡市拠点の福博会系の活動範囲に含まれるエリア。'
     '工藤會とは別系統だが、九州ヤクザ史の文脈で並列参照される。',
     '平成抗争', '福博会系'),

    ('kanda_industrial',
     '苅田町(工事関連事案)',
     13, 33.7794, 130.9694, 600,
     'district', None, None, 'active',
     '京築の苅田町。日産自動車九州工場などの大規模工事で'
     '建設業者の暴排対応事案が報じられた。',
     '平成抗争', '工藤會'),

    ('yukuhashi_periphery',
     '行橋市(京築の周辺都市)',
     16, 33.7283, 130.9772, 600,
     'district', None, None, 'active',
     '行橋市。京築地区の中核都市の一つ。'
     '北九州市東部と隣接し、関連事案の地理的伝播エリア。',
     '平成抗争', '工藤會'),

    # 司法・行政の細部
    ('kokurakita_police_station2',
     '小倉北警察署 暴対担当窓口',
     1, 33.8879, 130.8810, 25,
     'lore_site', None, None, 'active',
     '小倉北警察署内の暴対担当窓口は、地域住民・事業者向け相談の入口。'
     '頂上作戦以降、相談件数が大幅に増えた。',
     '頂上作戦', '県警側'),

    ('kokura_bouhai_office',
     '北九州市 暴追運動推進会議事務局',
     1, 33.8854, 130.8755, 50,
     'lore_site', None, None, 'active',
     '北九州市役所内の暴追運動推進会議事務局。'
     '神岳本部解体・跡地問題・地域連携の中継点だった機関。',
     '頂上作戦', '市民側'),

    # 文化・象徴
    ('wasshoi_summer_festival',
     '小倉「わっしょい百万夏まつり」会場',
     1, 33.8866, 130.8800, 200,
     'district', '1988', None, 'active',
     '小倉中心市街で毎年8月初旬に開催される夏祭り。'
     '頂上作戦以降は警察と祭り運営側の暴排対応が継続的に強化された。',
     '頂上作戦', '市民側'),

    ('kokura_higashi_school',
     '西小倉小学校など — 地域防犯教育',
     1, 33.8870, 130.8770, 100,
     'lore_site', None, None, 'active',
     '小倉北区の小学校群。神岳本部に近い小学校では、暴排教育が地域連携の '
     '一環として継続的に行われた。',
     '頂上作戦', '市民側'),

    # 中津 — 周辺都市の細部
    ('nakatsu_kudo_ato',
     '中津市(工藤組初代発祥地周辺・大分)',
     6, 33.5985, 131.1883, 600,
     'lore_site', '1953', '1987', 'historical',
     '大分県中津市。工藤組初代組長 工藤玄治の発祥地。'
     '現在は当時の組事務所跡を示す資料は乏しいが、'
     '関門海峡を跨ぐ「中津 — 門司 — 小倉」ラインの起点として位置づけられる。',
     '戦後闇市', '工藤組系'),

    # ===== 戦前史 =====
    ('yawata_seitetsu_1901',
     '八幡製鐵所 操業開始(1901-11-18)',
     9, 33.8730, 130.8085, 200,
     'lore_site', '1901-11-18', None, 'active',
     '官営八幡製鐵所 操業開始。明治政府の重工業計画の核として北九州が選ばれ、'
     '労働者の大量流入を生んだ。戦後の闇市・労働者街文化、'
     'ひいてはヤクザ系列の地理的分布の経済的根拠。',
     '戦後闇市', '市民側'),

    ('kokura_air_raid_1945',
     '小倉空襲・原爆代替標的(1945-08)',
     1, 33.8866, 130.8826, 800,
     'lore_site', '1944-08-19', '1945-08-09', 'historical',
     '小倉は第二次世界大戦末期に複数回空襲を受けた。'
     '1944-08-19 八幡空襲(第1次)・1945-06-25 八幡空襲(第2次)・'
     '1945-08-08 小倉空襲。'
     '1945-08-09 第二原爆の本来の標的は小倉(八幡製鐵所)だったが、'
     '雲と煙で目視できず長崎へ変更。戦後の街の風景の根本背景。',
     '戦後闇市', '市民側'),

    ('kokura_yamiichi_1946',
     '小倉駅前 戦後闇市萌芽地',
     1, 33.8860, 130.8820, 200,
     'lore_site', '1945-09', '1955', 'historical',
     '終戦直後、小倉駅前と旦過周辺に戦後闇市が形成された。'
     'GHQ 進駐期の物資配給崩壊と戦災での街区破壊が背景。'
     '草野一家・工藤組の発祥はこの闇市文化と地続きにある。',
     '戦後闇市', '草野一家系'),

    # ===== 食文化と街 =====
    ('sasashi_udon_first',
     '資さんうどん(1号店・北九州市)',
     7, 33.8595, 130.8830, 200,
     'lore_site', '1976', None, 'active',
     '小倉南区 資さんうどん 1号店。1976年創業。北九州市民の代名詞的存在で、'
     '繁華街・労働者街・郊外住宅地のすべてで深夜営業する庶民の場所。'
     '街の暴排運動の「日常側」を象徴する拠点として地元紙コラムに繰り返し登場。',
     '高度成長', '市民側'),

    ('horumon_district_sakaimachi',
     '堺町ホルモン店街',
     1, 33.8853, 130.8807, 60,
     'lore_site', '1960s', None, 'active',
     '堺町歓楽街の一角に集中するホルモン・モツ鍋・焼鳥店群。'
     '戦後の労働者街文化の延長で、八幡製鐵所労働者が「仕事帰りに集まる場所」 '
     'として育った食文化エリア。',
     '高度成長', '市民側'),

    ('kokura_yatai_corner',
     '小倉駅前 屋台横丁(往年の)',
     1, 33.8862, 130.8820, 80,
     'lore_site', '1950s', '1990s', 'historical',
     '戦後から平成初期まで小倉駅前一帯に存在した屋台横丁。'
     '闇市文化の直接の継承で、後に再開発で姿を消した。'
     '当時の屋台主には博徒系の縁を持つ者もいたと地元紙の回顧連載は記録する。',
     '戦後闇市', '市民側'),

    # ===== メディア・カルチャー =====
    ('crows_kitakyu_setting',
     '「クローズ」「Worst」の舞台 — 北九州',
     1, 33.8830, 130.8770, 1500,
     'lore_site', '1990s', None, 'active',
     '高橋ヒロシの漫画「クローズ」「Worst」の舞台「鈴蘭高校」は、'
     '作者が北九州市出身であることから北九州近隣がモデルとされる。'
     '工藤會時代の北九州の不良文化が、戦後ヤクザ文化と地続きで描かれた。',
     '平成抗争', '市民側'),

    ('mojiport_kitagata_book',
     '門司港 — 北方謙三「ブラディ・ドール」の舞台',
     3, 33.9447, 130.9628, 400,
     'lore_site', '1980s', None, 'active',
     '北方謙三の「ブラディ・ドール」シリーズ(1980年代後半)は、'
     '門司港のバー「ブラディ・ドール」を舞台にした犯罪小説連作。'
     '戦後港町の暗部と組織犯罪文化の文学化として知られる。',
     '高度成長', '工藤組系'),

    ('ryugagotoku_virtual',
     '「龍が如く」シリーズ — 架空の神室町',
     1, 33.8866, 130.8826, 0,
     'lore_site', '2005', None, 'active',
     'セガ「龍が如く」シリーズ(2005-)は架空の「神室町」(歌舞伎町モデル)を舞台に '
     '日本のヤクザ文化を国際的に広めた。'
     '工藤會を直接描かないが、特定危険指定時代の海外受容の背景として並列参照。',
     '平成抗争', '工藤會'),

    # ===== 全国比較・指定暴力団 =====
    ('compare_yamaguchigumi_hq',
     '六代目山口組 総本部(神戸)',
     6, 34.7045, 135.1958, 300,
     'lore_site', '1915', None, 'active',
     '兵庫県神戸市灘区。全国最大の指定暴力団 六代目山口組の総本部。'
     '工藤會とは別系統だが、全国の指定暴力団情勢の中核として並列比較される。',
     '高度成長', '山口組系'),

    ('compare_sumiyoshi_hq',
     '住吉会 — 東京',
     6, 35.6720, 139.7635, 1000,
     'lore_site', '1958', None, 'active',
     '東京拠点の指定暴力団 住吉会。山口組と並ぶ全国2強の片翼。'
     '工藤會と異なり東日本拠点で、市民を直接標的とする手口は報じられていない。',
     '高度成長', '司法側'),

    ('compare_inagawakai_hq',
     '稲川会 — 東京・横浜',
     6, 35.4437, 139.6380, 1500,
     'lore_site', '1949', None, 'active',
     '東京・神奈川を中心とする指定暴力団 稲川会。全国の主要3組織の一つ。'
     '工藤會と異なり関東を本拠とし、組織構造や手口の系統が異なる。',
     '高度成長', '司法側'),

    ('compare_aizukotetsu_hq',
     '会津小鉄会 — 京都',
     6, 35.0036, 135.7681, 800,
     'lore_site', '1869', None, 'active',
     '京都拠点の指定暴力団 会津小鉄会。明治期創設という長い歴史を持つ。'
     '関西の地場連合体として九州とは別系統で論じられる。',
     '戦後闇市', '司法側'),

    ('compare_kyokutokai_hq',
     '極東会 — 関東テキ屋系',
     6, 35.7100, 139.7800, 1200,
     'lore_site', '1950s', None, 'active',
     '関東を中心とする指定暴力団 極東会。テキ屋系の系譜で、'
     '工藤會のような博徒+地場連合体とは出自が異なる。',
     '高度成長', '司法側'),

    ('compare_namikawakai_hq',
     '浪川会 — 久留米(旧九州誠道会)',
     11, 33.3192, 130.5083, 400,
     'lore_site', '2013', None, 'active',
     '久留米拠点の指定暴力団 浪川会。'
     '2013年に九州誠道会の解散届を受けて再編。九州抗争の余波を残す組織。',
     '解体後', '道仁会系'),

    ('compare_kyokuseikai_hq',
     '共政会 — 広島',
     6, 34.3973, 132.4592, 1000,
     'lore_site', '1963', None, 'active',
     '広島拠点の指定暴力団 共政会。「孤狼の血」シリーズの背景となる '
     '広島ヤクザ史を構成する組織の一つ。工藤會研究と並列で語られる。',
     '高度成長', '司法側'),

    ('compare_kyokuryukai_hq',
     '旭琉会 — 沖縄',
     6, 26.2123, 127.6792, 1500,
     'lore_site', '1949', None, 'active',
     '沖縄県を本拠とする指定暴力団 旭琉会。米軍統治・本土復帰の特殊な歴史背景を持つ。'
     '全国の指定暴力団の中で地理的にも歴史的にも独特の存在。',
     '戦後闇市', '司法側'),

    # ===== 国際比較 =====
    ('intl_cosa_nostra_italy',
     'イタリア コーザ・ノストラ(シチリア)',
     6, 38.1157, 13.3613, 5000,
     'lore_site', '1860s', None, 'active',
     'シチリア島を中心とするイタリアマフィア コーザ・ノストラ。'
     '組織犯罪研究の比較対象として、工藤會を含む日本のヤクザと並列で論じられる。'
     'Andrew Rankin など海外研究は両者を構造的に比較してきた。',
     '戦後闇市', '司法側'),

    ('intl_ndrangheta_italy',
     'イタリア \'ンドランゲタ(カラブリア)',
     6, 38.9100, 16.5874, 5000,
     'lore_site', '1860s', None, 'active',
     '南イタリア・カラブリア州を本拠とする \'ンドランゲタ。'
     '現在のイタリアで最も強力なマフィアとされる。'
     '工藤會研究の国際比較では「血縁ベースの結束と現代的な暴力管理」の対比として参照。',
     '解体後', '司法側'),

    ('intl_triads_hk',
     '香港 三合会',
     6, 22.3193, 114.1694, 5000,
     'lore_site', '1700s', None, 'active',
     '香港の三合会は中国系犯罪組織群の総称。'
     'アジア組織犯罪研究で工藤會と並列で参照される代表事例。',
     '戦後闇市', '司法側'),

    ('intl_la_cosa_nostra_us',
     '米国 La Cosa Nostra(LCN)',
     6, 40.7128, -74.0060, 5000,
     'lore_site', '1900s', None, 'active',
     '米国マフィア La Cosa Nostra。FBI による継続的捜査対象。'
     '組織トップを共謀罪・RICO 法で立件するモデルは、'
     '工藤會頂上作戦の捜査方針との比較で論じられる。',
     '戦後闇市', '司法側'),

    ('intl_mekong_compounds_ref',
     'メコン地域 詐欺コンパウンド(SS プロジェクト参照)',
     6, 16.6890, 98.2680, 50000,
     'lore_site', '2018', None, 'active',
     'ミャンマー・カンボジア国境のメコン地域に集中するオンライン詐欺コンパウンド群。'
     '本マップの姉妹プロジェクト「Compound Time Machine」が扱う対象。'
     '日本のヤクザの国際展開とは別系統だが、組織犯罪 OSINT の現代的対象として並列。',
     '解体後', '司法側'),

    # ===== 金融・反社対応 =====
    ('mizuho_bank_hq',
     'みずほ銀行(反社融資問題 2013)',
     6, 35.6852, 139.7625, 200,
     'lore_site', '2013', '2014', 'historical',
     '2013-2014年、みずほ銀行が暴力団関係先への融資を継続していた問題が表面化。'
     '銀行業界全体の反社チェック体制の見直しの契機になった。'
     '工藤會を含む指定暴力団との金融面の遮断が大幅に強化される節目。',
     '平成抗争', '司法側'),

    ('zenginkyo_compliance',
     '全国銀行協会(反社条項標準化)',
     6, 35.6839, 139.7625, 100,
     'lore_site', '2008', None, 'active',
     '全国銀行協会が反社条項の標準化を進めた中核機関。'
     '取引約款への反社条項組み込み、口座開設時の反社チェックの全国展開を主導。',
     '平成抗争', '司法側'),

    # ===== 雑誌・メディア =====
    ('magazine_tsukuru',
     '月刊『創』(つくる)— ヤクザ特集',
     6, 35.7000, 139.7700, 100,
     'lore_site', '1971', None, 'active',
     '月刊『創』は1971年創刊。指定暴力団・ヤクザ社会の特集を継続的に組む '
     '社会派雑誌。工藤會を含む特定危険指定の特集も多数掲載してきた。',
     '平成抗争', '著作者'),

    ('jitsuwa_magazines',
     '実話誌グループ(各誌編集部)',
     6, 35.7100, 139.7700, 100,
     'lore_site', '1980s', None, 'active',
     '『週刊実話』『実話ドキュメント』『実話BUNKAタブー』『アサヒ芸能』など、'
     '実話系雑誌はヤクザ社会の詳細を継続的に扱ってきた。'
     '報道書籍・地元紙とは別系統の情報源として参照されるが、検証の必要性は高い。',
     '平成抗争', '著作者'),
]


CHRONICLE = [
    # ord, year_label, title, body, era_tag, faction_tag
    (10, '1947', '草野一家結成',
     '初代総長 草野高明が小倉で草野一家を結成(戦後の地場テキ屋系から成長)。'
     '小倉北区を中心に勢力を伸ばす。',
     '戦後闇市', '草野一家系'),
    (20, '1953', '工藤組結成(大分・中津)',
     '初代組長 工藤玄治が大分県中津市で工藤組を結成。後年、北九州への進出と'
     '草野一家との連携が進む。',
     '戦後闇市', '工藤組系'),
    (25, '1980s', '山口組九州進出と防衛戦',
     '1980年代に山口組系列が九州進出を強化。北九州の地場組織との緊張が高まり、'
     '工藤会・草野一家は防衛側として共闘姿勢を強める。後の連合体成立への伏線。',
     '高度成長', '山口組系'),
    (30, '1987', '工藤連合草野一家成立',
     '工藤会と草野一家が統合し「工藤連合草野一家」となる。本拠を小倉北区神岳に置く。',
     '高度成長', '工藤會'),
    (35, '2000', '工藤會へ改称',
     '名称を「工藤會」に統一。野村悟が会長に就任(三代目総裁制から会長制へ移行)。'
     '田中組はじめ複数の傘下団体を擁する連合体となる。',
     '平成抗争', '工藤會'),
    (40, '2003', '平成新天地事件',
     '小倉北区の歓楽街で発生した一連の襲撃・脅迫事件が「平成新天地事件」として報道された。'
     '工藤會の市民威迫の手口が表面化する転機。',
     '平成抗争', '工藤會'),
    (45, '2006-2013', '道仁会・誠道会代理戦争(九州抗争)',
     '久留米拠点の道仁会と分派の九州誠道会(後の浪川会)による抗争が九州全体に拡大。'
     '北九州にも飛び火し、工藤會の縄張りに緊張をもたらす。',
     '平成抗争', '道仁会系'),
    (50, '2008', '指定暴力団に再指定',
     '福岡県公安委員会が工藤會を指定暴力団に再指定。市民を巻き込む手口が問題化。',
     '平成抗争', '司法側'),
    (60, '2012-12', '特定危険指定暴力団へ',
     '改正暴対法に基づき、工藤會が全国で初めて「特定危険指定暴力団」に指定される。'
     '事務所使用制限・脱退妨害禁止など強い規制対象に。',
     '平成抗争', '司法側'),
    (70, '2014-09-11', '頂上作戦 — トップ逮捕',
     '福岡県警が野村悟・田上不美夫を相次いで逮捕。「市民襲撃4事件」の指示者として、'
     '組織のトップを首謀者として立件する異例の捜査。',
     '頂上作戦', '県警側'),
    (75, '2014-2019', '田中組系列の離脱と分裂',
     '頂上作戦以降、工藤會傘下の主要組「田中組」を中心に組員離脱と分裂が進行。'
     '報道された組事務所撤去が相次いだ。',
     '頂上作戦', '田中組系'),
    (80, '2019-07', '本部解体・「金看板」撤去',
     '工藤會本部(小倉北区神岳1丁目)が解体着手。同8月までに更地化。'
     '本部正面の金属製看板撤去の絵は全国に流れ、指定暴力団の象徴喪失として報じられた。',
     '頂上作戦', '工藤會'),
    (90, '2021-08-24', '一審 福岡地裁判決',
     '福岡地裁、野村悟に死刑、田上不美夫に無期懲役を言い渡す。'
     '指定暴力団トップに死刑判決は史上初。判決後、野村被告が「生涯後悔するぞ」と '
     '述べたとされる発言が報じられた。',
     '頂上作戦', '司法側'),
    (95, '2022-04 / 08', '旦過市場 二度の大火',
     '工藤會本部から徒歩圏の旦過市場で4月19日と8月10日に大規模火災。'
     '工藤會事件との直接の関連は公式には認定されていないが、街の現代史の節目に。',
     '解体後', '市民側'),
    (100, '2024-03-12', '控訴審 福岡高裁判決',
     '福岡高裁、野村悟への死刑判決を破棄し無期懲役に減刑。田上不美夫は一審維持。'
     '状況証拠の評価をめぐる判断が一審と分かれた。',
     '解体後', '司法側'),
    (110, '2024-12', '特定危険指定の更新',
     '工藤會の特定危険指定暴力団としての指定が3年更新。'
     '構成員数は頂上作戦以前から大幅減も、規制対象の地位は維持。',
     '解体後', '司法側'),
]


PROSECUTIONS = [
    # ord, case_label, defendant_label, court, stage, decided_on, outcome, summary
    (10, '頂上作戦 市民襲撃4事件統合公判', '野村悟', '福岡地方裁判所', '一審',
     '2021-08-24', '死刑',
     '元漁協理事射殺(1998)・元警察官襲撃(2012)・看護師襲撃(2013)・歯科医師襲撃(2014)'
     'の4事件すべての首謀者と認定。指定暴力団トップへの死刑判決は史上初。'),
    (20, '頂上作戦 市民襲撃4事件統合公判', '田上不美夫', '福岡地方裁判所', '一審',
     '2021-08-24', '無期懲役',
     '野村被告と共謀して市民襲撃を指示したと認定。'),
    (30, '頂上作戦 市民襲撃4事件統合公判', '野村悟', '福岡高等裁判所', '控訴審',
     '2024', '(phase9 で出典確定)',
     '一審死刑判決に対する控訴審。詳細は phase9_testimony で公開判決から確定。'),
    (40, '頂上作戦 市民襲撃4事件統合公判', '田上不美夫', '福岡高等裁判所', '控訴審',
     '2024', '(phase9 で出典確定)',
     '一審無期懲役判決に対する控訴審。'),
]


def main():
    if os.path.exists(DB):
        # SS-style: idempotent, but we never destructively drop. We just create
        # tables if missing and re-insert seeds with REPLACE semantics on slug/ord.
        print(f'kokura.db exists; refreshing schema and reseeding base rows.')
    else:
        print(f'creating fresh kokura.db at {DB}')

    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)

    # Seed places
    con.executemany(
        'INSERT OR REPLACE INTO place(id, name_canonical, admin_country, admin_state, '
        ' centroid_lat, centroid_lon) VALUES (?,?,?,?,?,?)',
        PLACES,
    )

    # Seed sites (keyed by slug, UPDATE in place to preserve ids — otherwise
    # downstream phases that reference site_id orphan).
    for row in SITES:
        (slug, label, place_id, lat, lon, unc, kind, fs, ls, status, notes,
         era, faction) = row
        existing = con.execute('SELECT id FROM site WHERE slug=?', (slug,)).fetchone()
        if existing:
            con.execute(
                'UPDATE site SET label=?, place_id=?, rep_lat=?, rep_lon=?, '
                ' uncertainty_m=?, kind=?, first_seen=?, last_seen=?, status=?, '
                ' notes=?, era_tag=?, faction_tag=? WHERE id=?',
                (label, place_id, lat, lon, unc, kind, fs, ls, status, notes,
                 era, faction, existing[0]),
            )
        else:
            con.execute(
                'INSERT INTO site(slug, label, place_id, rep_lat, rep_lon, uncertainty_m, '
                ' kind, first_seen, last_seen, status, notes, era_tag, faction_tag) '
                ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (slug, label, place_id, lat, lon, unc, kind, fs, ls, status, notes,
                 era, faction),
            )

    # Reseed chronicle by ord
    con.execute('DELETE FROM chronicle')
    con.executemany(
        'INSERT INTO chronicle(ord, year_label, title, body, era_tag, faction_tag) '
        'VALUES (?,?,?,?,?,?)',
        CHRONICLE,
    )

    # Reseed prosecution by ord
    con.execute('DELETE FROM prosecution')
    con.executemany(
        'INSERT INTO prosecution(ord, case_label, defendant_label, court, stage, '
        ' decided_on, outcome, summary) VALUES (?,?,?,?,?,?,?,?)',
        PROSECUTIONS,
    )

    con.commit()

    # Print a quick summary
    for tbl in ('place', 'site', 'chronicle', 'prosecution'):
        n = con.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()[0]
        print(f'  {tbl}: {n} rows')

    con.close()
    print('init_db.py done.')


if __name__ == '__main__':
    main()
