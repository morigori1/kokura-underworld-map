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

    # ===== 久留米 深掘り =====
    ('kurume_dojinkai_main_hq',
     '道仁会 本部(久留米市)',
     11, 33.3201, 130.5063, 100,
     'hq_current', '1971', None, 'active',
     '久留米市内の道仁会本部。1971年結成、九州地場の主要指定暴力団。'
     '工藤會とは別系統だが、九州ヤクザ史の中核として並列される。',
     '高度成長', '道仁会系'),

    ('kurume_seidokai_hq',
     '九州誠道会 本部跡(久留米市)',
     11, 33.3175, 130.5096, 200,
     'hq_former', '2006', '2013', 'demolished',
     '2006年に道仁会から分派した九州誠道会の本部。'
     '6年に及ぶ「九州抗争」の一方の主体。2013年解散届で消滅、浪川会に再編。',
     '平成抗争', '道仁会系'),

    ('kurume_namikawakai_hq',
     '浪川会 本部(久留米市)',
     11, 33.3180, 130.5093, 150,
     'hq_current', '2013', None, 'active',
     '2013年、九州誠道会の解散届を受けて再編成された浪川会の本部。'
     '抗争の沈静化と組織の継続を象徴する転換点。',
     '解体後', '道仁会系'),

    ('kurume_bunkagai_central',
     '久留米 文化街 中央(歓楽街・抗争激発エリア)',
     11, 33.3252, 130.5078, 80,
     'attack_site', '2006', '2013', 'historical',
     '久留米市の中心歓楽街「文化街」。九州抗争(2006-2013)中、'
     '発砲・襲撃事件が断続的に発生。「夜が静かだった」と地元紙が表現した暗黒期。',
     '平成抗争', '道仁会系'),

    ('kurume_west_arcade',
     '久留米 西鉄久留米駅周辺',
     11, 33.3142, 130.5102, 150,
     'district', None, None, 'active',
     '西鉄久留米駅周辺の商業エリア。久留米の動線中心で、'
     '抗争期に巻き添えへの不安が市民に広がった場所。',
     '平成抗争', '道仁会系'),

    ('kurume_jr_station',
     'JR 久留米駅(新幹線停車駅)',
     11, 33.3128, 130.5232, 80,
     'landmark', '1890', None, 'active',
     'JR 久留米駅。新幹線停車駅で福岡市・熊本市・北九州市を結ぶ動線の中継点。'
     '九州抗争期は出入りが警戒された玄関口。',
     '高度成長', '市民側'),

    ('amagi_periphery',
     '甘木(朝倉市・抗争北端)',
     11, 33.4252, 130.6747, 800,
     'attack_site', '2006', '2013', 'historical',
     '朝倉市甘木地区。久留米の北、北九州方面への動線上にあり、'
     '九州抗争で関連事件が複数報じられた。',
     '平成抗争', '道仁会系'),

    ('arao_omuta',
     '荒尾市(熊本・抗争南端)',
     17, 32.9817, 130.4445, 800,
     'attack_site', '2008', '2013', 'historical',
     '熊本県荒尾市は大牟田市と隣接。九州抗争の南端で、'
     '熊本県側にも飛び火した関連事件が断続的に報道された。',
     '平成抗争', '道仁会系'),

    ('saga_periphery_kyushu_war',
     '佐賀県内(九州抗争 西端)',
     11, 33.2494, 130.2989, 5000,
     'attack_site', '2007', '2012', 'historical',
     '佐賀県内でも九州抗争関連の発砲事件が報じられた。'
     '九州中部から西部への抗争の地理的広がりを示す。',
     '平成抗争', '道仁会系'),

    ('kurume_keisatsu',
     '久留米警察署 + 福岡県警久留米地区',
     11, 33.3168, 130.5161, 80,
     'landmark', None, None, 'active',
     '久留米警察署。九州抗争期(2006-2013)、福岡県警は本署を拠点に '
     '特別警戒態勢を継続。終結後も道仁会対策の継続拠点。',
     '頂上作戦', '県警側'),

    ('kurume_shrine_temple',
     '久留米市 高良大社 周辺',
     11, 33.3070, 130.5577, 600,
     'landmark', None, None, 'active',
     '久留米の総鎮守 高良大社。'
     '九州抗争期にも初詣・例祭は通常開催され、'
     '「祭りの日常」と「街の異常」の対比が地元紙コラムに残る。',
     '高度成長', '市民側'),

    # ===== 神戸・山口組史 深掘り =====
    ('kobe_yamaguchi_souhonbu',
     '六代目山口組 総本部(神戸市灘区)',
     6, 34.7045, 135.1958, 100,
     'hq_current', '1915', None, 'active',
     '兵庫県神戸市灘区篠原本町。六代目山口組総本部。'
     '日本最大の指定暴力団の中枢。'
     '工藤會とは別系統だが、全国組織犯罪情勢の基準点として参照される。',
     '高度成長', '山口組系'),

    ('kobe_yamaguchi_origin',
     '山口春吉 — 山口組創設(1915)',
     6, 34.6800, 135.1850, 800,
     'lore_site', '1915', None, 'historical',
     '神戸港の労働者監督として山口春吉が山口組を結成(1915年)。'
     '神戸港の港湾労働の歴史と山口組の系譜は地続き。'
     '110 年以上の歴史を持つ日本最古級のヤクザ系統の一つ。',
     '戦後闇市', '山口組系'),

    ('kobe_kobeyamaguchigumi_hq',
     '神戸山口組 本部(2015分裂後)',
     6, 34.7100, 135.2050, 400,
     'hq_current', '2015-08-27', None, 'active',
     '2015年8月27日の六代目山口組分裂で結成された神戸山口組の本部。'
     '兵庫県内に拠点を置く。「親分の絆」を強調した分派。',
     '頂上作戦', '山口組系'),

    ('kobe_kizunakai_hq',
     '絆會(旧任侠山口組)本部',
     6, 34.7150, 135.2100, 400,
     'hq_current', '2017-04', None, 'active',
     '2017年4月、神戸山口組から分派して任侠山口組を結成。'
     '2020年1月に絆會へ改称。「ヤクザ三派対立」構図の片翼。',
     '頂上作戦', '山口組系'),

    ('kobe_yamaichi_ground_zero',
     '山一抗争 主戦場(1985-1989・神戸/大阪)',
     6, 34.7000, 135.2000, 2000,
     'attack_site', '1985-08-27', '1989', 'historical',
     '三代目山口組と一和会の抗争「山一抗争」の主戦場。'
     '5年に及ぶ全国規模の襲撃で約300件以上の事件が報じられた。'
     '一般市民巻き添えへの懸念から、後の暴対法(1991)成立の社会的背景に。',
     '高度成長', '山口組系'),

    ('osaka_yamaguchi_kizunabashi',
     '大阪 — 山口組の関西第二中枢',
     6, 34.6937, 135.5023, 5000,
     'lore_site', '1950s', None, 'active',
     '大阪は山口組の関西第二中枢。神戸本部と並び、'
     '関西の組織犯罪情勢の中核。山口組の九州・北九州への進出ラインも '
     'この大阪を中継地とした、と関連書籍は描く。',
     '高度成長', '山口組系'),

    ('hyogo_keisatsu_hq',
     '兵庫県警察 本部(山口組対応)',
     6, 34.6900, 135.1800, 200,
     'landmark', None, None, 'active',
     '兵庫県警察本部。六代目山口組・神戸山口組両方の対応の主軸。'
     '頂上作戦と並走する形で2020年の特定抗争指定対応を行った。',
     '頂上作戦', '県警側'),

    ('shinobu_tsukasa_kobe',
     '司忍 — 六代目山口組組長',
     6, 34.7045, 135.1958, 200,
     'lore_site', '2005-', None, 'active',
     '司忍(つかさ しのぶ)は六代目山口組組長(2005-)。'
     '工藤會の野村悟と同時代の組織トップ。'
     '司忍は組織犯罪の世界では神戸を本拠とする全国体の頂点として位置づく。',
     '頂上作戦', '山口組系'),

    # ===== 東京・住吉会・稲川会 深掘り =====
    ('tokyo_sumiyoshi_hq',
     '住吉会 本部(東京・赤坂)',
     6, 35.6749, 139.7370, 200,
     'hq_current', '1958', None, 'active',
     '東京都港区赤坂の住吉会本部。1958年起源。'
     '関東を本拠とする指定暴力団で、山口組と並ぶ全国2強の片翼。',
     '高度成長', '司法側'),

    ('tokyo_inagawakai_hq',
     '稲川会 本部(東京)',
     6, 35.6580, 139.7440, 200,
     'hq_current', '1949', None, 'active',
     '東京都港区六本木の稲川会本部。1949年起源。'
     '神奈川・東京を中心とする指定暴力団。'
     '稲川聖城(初代)を起点とし、戦後ヤクザ史の主要組織の一つ。',
     '高度成長', '司法側'),

    ('tokyo_kabukicho',
     '新宿歌舞伎町(ヤクザ表象の中心地)',
     6, 35.6938, 139.7034, 500,
     'district', '1950s', None, 'active',
     '東京新宿の歓楽街。住吉会・極東会など複数組織の縄張りが交錯する '
     '日本最大級の歓楽街。「龍が如く」の神室町・「Tokyo Vice」の舞台のモデルでもあり、'
     '海外メディアでの日本ヤクザ表象の中心地。',
     '高度成長', '司法側'),

    ('tokyo_shibuya_yakuza',
     '渋谷(半グレ・準暴力団の中心地)',
     6, 35.6580, 139.7016, 500,
     'district', '2000s', None, 'active',
     '渋谷は2000年代以降、半グレ・準暴力団の活動が報じられた地域。'
     '従来の指定暴力団系列とは別系統で、警察庁の「準暴力団」概念創設(2013)の '
     '直接の背景。工藤會とは別文脈の現代型組織犯罪。',
     '解体後', '司法側'),

    ('tokyo_yakuzas_hubs',
     '東京 — 関東地場連合の集中',
     6, 35.6762, 139.6503, 1500,
     'lore_site', '1950s', None, 'active',
     '東京は住吉会・稲川会・極東会・松葉会・国粋会など、'
     '関東地場連合の指定暴力団が複数本拠を置く集中地。'
     '工藤會の九州地場とは別系統で、関東 vs 九州の組織犯罪文化の対比軸。',
     '高度成長', '司法側'),

    ('tokyo_metro_keisatsu',
     '警視庁 本部(山口組・住吉会・稲川会対応)',
     6, 35.6757, 139.7560, 200,
     'landmark', None, None, 'active',
     '東京都千代田区の警視庁本部。住吉会・稲川会など関東主要組織の対応の主軸。'
     '工藤會のような市民威迫の手口は管轄組織には少ないが、'
     '全国の組織犯罪情報の集約点として機能。',
     '頂上作戦', '県警側'),

    ('tokyo_diet_again',
     '国会(暴対法成立・改正の地)',
     6, 35.6758, 139.7447, 100,
     'lore_site', '1991', None, 'active',
     '東京・永田町の国会議事堂。山一抗争(1989)を受けた暴対法の成立(1991-05)、'
     '工藤會への特定危険指定創設(2012改正)など、'
     '全国の組織犯罪規制を作る場所。工藤會マップの全国的な「立法軸」。',
     '高度成長', '司法側'),

    ('tokyo_finance_district',
     '東京 大手町・丸の内(銀行業界の反社対応中心)',
     6, 35.6814, 139.7670, 400,
     'lore_site', '2007', None, 'active',
     '東京・大手町・丸の内のメガバンク本店街。'
     '2007年の反社遮断指針・2013-2014のみずほ事件・反社条項標準化など、'
     '銀行業界の反社対応の中心。工藤會を含む指定暴力団の金融遮断の起点。',
     '平成抗争', '司法側'),

    ('tokyo_fsa',
     '金融庁(反社対応の規制主体)',
     6, 35.6750, 139.7620, 100,
     'landmark', '1998', None, 'active',
     '東京・霞が関の金融庁。みずほ銀行業務改善命令(2014)・'
     '暗号資産取引所反社対応強化(2018-)など、'
     '工藤會を含む指定暴力団の金融取引を遮断する規制主体。',
     '平成抗争', '司法側'),

    ('tokyo_npa_hq',
     '警察庁(全国組織犯罪対策本部)',
     6, 35.6759, 139.7570, 100,
     'landmark', None, None, 'active',
     '東京・霞が関の警察庁。全国の指定暴力団情勢を集約し、'
     '警察白書を毎年公表。工藤會頂上作戦の捜査方針の方向付けにも関与。',
     '頂上作戦', '県警側'),

    ('tokyo_us_embassy',
     '米国大使館(OFAC TCO 指定の調整地)',
     6, 35.6700, 139.7400, 150,
     'lore_site', '2013', None, 'active',
     '東京・赤坂の米国大使館。2013-02-23 の OFAC 工藤會 TCO 指定は '
     '日米当局間の事前協議を経て行われたと報じられた。'
     '国際的金融制裁の起点。',
     '平成抗争', '司法側'),

    # ===== 広島・共政会 深掘り =====
    ('hiroshima_kyoseikai_hq',
     '共政会 本部(広島市中区)',
     6, 34.3963, 132.4574, 200,
     'hq_current', '1963', None, 'active',
     '広島市中区の共政会本部。1963年起源(初代山村辰雄)。'
     '中国地方最大の指定暴力団で、広島ヤクザ史の中核。'
     '「孤狼の血」シリーズの背景となる組織。',
     '高度成長', '司法側'),

    ('hiroshima_yakuza_war',
     '広島抗争 主戦場(1963-1972 / 仁義なき戦い舞台)',
     6, 34.3850, 132.4700, 1500,
     'attack_site', '1963', '1972', 'historical',
     '広島市中心市街地。1960年代の山口組進出と地場組織の抗争「広島抗争」の主戦場。'
     '深作欣二「仁義なき戦い」シリーズ(1973-1974)の直接の素材。'
     '工藤會時代より20年早い、戦後ヤクザ抗争の典型事例。',
     '高度成長', '司法側'),

    ('hiroshima_nagarekawa',
     '流川(広島市中心歓楽街)',
     6, 34.3953, 132.4615, 200,
     'district', '1950s', None, 'active',
     '広島市中区の歓楽街「流川(ながれかわ)」。'
     '広島の組織犯罪と歓楽街文化が交わる中心地。'
     '「孤狼の血」シリーズの舞台として描かれる。',
     '高度成長', '司法側'),

    ('hiroshima_atomic_park',
     '原爆ドーム + 平和記念公園(戦後広島の出発点)',
     6, 34.3955, 132.4536, 100,
     'lore_site', '1945-08-06', None, 'active',
     '広島市中区の原爆ドーム・平和記念公園。'
     '1945-08-06 の原爆投下から戦後広島が始まった。'
     '小倉(原爆代替標的)との対比で、戦後北九州・広島の両都市の戦後史の '
     '出発点を結ぶ象徴的地点。',
     '戦後闇市', '市民側'),

    ('hiroshima_kyoseikai_offshoots',
     '広島組系 系列(共政会・浅野組・親和会・侠道会)',
     6, 34.3950, 132.4650, 800,
     'lore_site', '1960s', None, 'active',
     '広島の指定暴力団は共政会のほか、浅野組(尾道)・親和会(神戸寄り)・'
     '侠道会(尾道)など複数系列。'
     '工藤會のような単一中心ではない、複数系列が並存する構造。',
     '高度成長', '司法側'),

    ('hiroshima_keisatsu',
     '広島県警察 本部',
     6, 34.3960, 132.4595, 100,
     'landmark', None, None, 'active',
     '広島県警察本部。広島抗争(1963-1972)後の組織犯罪対策の蓄積を持つ。'
     '頂上作戦と並列で語られる地方警察の対応事例。',
     '頂上作戦', '県警側'),

    ('hiroshima_korou_no_chi',
     '「孤狼の血」舞台 — 広島ヤクザ史の文学化',
     6, 34.3960, 132.4630, 400,
     'lore_site', '2015', None, 'active',
     '柚月裕子原作・役所広司主演「孤狼の血」シリーズ(2015 原作・2018-2021 映画化)。'
     '広島抗争の系譜を文学化した代表作。'
     '工藤會頂上作戦と並列で「暴対法時代の地方都市と組織犯罪」の物語として読まれる。',
     '頂上作戦', '司法側'),

    ('hiroshima_jingi_movie',
     '「仁義なき戦い」舞台 — 1973-1974 深作映画',
     6, 34.3850, 132.4700, 600,
     'lore_site', '1973', '1974', 'historical',
     '深作欣二監督「仁義なき戦い」シリーズ(1973-1974)は、'
     '広島抗争を直接の素材とする日本映画史の傑作。'
     '工藤會時代より40年前の作品だが、'
     '日本のヤクザ表象の原型を形成した作品として並列参照される。',
     '高度成長', '著作者'),

    ('hiroshima_kyoseikai_designation',
     '共政会 指定暴力団指定',
     6, 34.3963, 132.4574, 200,
     'lore_site', '1992', None, 'active',
     '1992年の暴対法施行第1陣で、共政会は指定暴力団に。'
     '工藤連合草野一家(後の工藤會)と同時期の指定。'
     '広島ヤクザ史と九州ヤクザ史の並走する規制史。',
     '高度成長', '司法側'),

    # ===== 半グレ・準暴力団・トクリュウ =====
    ('roppongi_clubs_hangure',
     '六本木 — 半グレ縄張り(関東連合)',
     6, 35.6627, 139.7320, 400,
     'district', '2000s', '2014', 'historical',
     '東京港区六本木のクラブ街。2000年代後半-2010年代前半に「関東連合」 '
     'などの半グレ集団が縄張りを持った。'
     '指定暴力団の系列ではない現代型組織犯罪の代表エリア。',
     '頂上作戦', '司法側'),

    ('kanto_rengo_hq',
     '関東連合(半グレ代表団体)',
     6, 35.6630, 139.7325, 300,
     'lore_site', '2000s', '2014', 'historical',
     '関東連合(かんとうれんごう)は2000年代後半-2010年代前半の '
     '代表的半グレ集団。元暴走族系・暴力団系の若者が結成。'
     '2012年の六本木クラブ襲撃事件で全国的に注目された。',
     '頂上作戦', '司法側'),

    ('roppongi_flower_attack',
     '六本木クラブ襲撃事件(2012-09-02)現場',
     6, 35.6627, 139.7320, 100,
     'attack_site', '2012-09-02', '2012-09-02', 'historical',
     '2012年9月2日、東京六本木のクラブで関東連合系の襲撃事件が発生。'
     '一般客が死亡。半グレ問題が全国的にメディアで取り上げられる '
     '転換点となった事件。',
     '頂上作戦', '司法側'),

    ('doragon_chinese_hangure',
     '怒羅権(ドラゴン)— 中国残留孤児系半グレ',
     6, 35.6760, 139.6500, 800,
     'lore_site', '1980s', None, 'active',
     '怒羅権(どらごん)は中国残留孤児の二世・三世を中心とする半グレ集団。'
     '東京・江戸川区を中心に活動。関東連合より長い歴史を持ち、'
     '現代型組織犯罪の系譜の一つとして報道される。',
     '解体後', '司法側'),

    ('komae_robbery_2023',
     '狛江市 強盗殺人事件(2023-01-19)現場',
     6, 35.6342, 139.5750, 300,
     'attack_site', '2023-01-19', '2023-01-19', 'historical',
     '2023年1月19日、東京都狛江市で高齢女性を狙った強盗殺人事件。'
     '「ルフィ事件」と呼ばれ、フィリピン拠点の指示役と日本国内の '
     '実行役(闇バイト)による初の組織的トクリュウ事件として全国的に報じられた。',
     '解体後', '司法側'),

    ('philippines_luffy_base',
     'フィリピン入管施設(ルフィ等指示拠点・2020-2023)',
     6, 14.5995, 120.9842, 5000,
     'lore_site', '2020', '2023-02', 'historical',
     'フィリピン・マニラの入管施設に収容されていた日本人4人(ルフィら)が、'
     '施設内から SNS・通話で日本の闇バイト実行役に指示。'
     '2023年2月に強制送還、日本で逮捕。'
     'トクリュウ事件の国際的指揮拠点として世界的に注目された。',
     '解体後', '司法側'),

    ('shinagawa_yamiarbeit_2024',
     '東京 — 2023-2024 連続強盗 多発エリア',
     6, 35.6580, 139.7016, 5000,
     'attack_site', '2023-09', '2024', 'historical',
     '2023年9月以降、東京・神奈川・千葉・茨城・栃木で連続強盗事件が多発。'
     'いずれも SNS で募集された闇バイト実行役が指示役の指示で実行する '
     'トクリュウ型犯罪。各事件で高齢者被害が多い。',
     '解体後', '司法側'),

    ('npa_tokuryu_office',
     '警察庁 — トクリュウ対策室(2024-)',
     6, 35.6759, 139.7570, 100,
     'lore_site', '2024', None, 'active',
     '警察庁は2024年、トクリュウ(匿名・流動型犯罪グループ)対策を強化。'
     '従来の指定暴力団・準暴力団に加えて、流動的・短期的に形成される '
     '新型組織犯罪を捕捉する枠組み。'
     '工藤會のような長期的組織犯罪とは別系統の対応。',
     '解体後', '司法側'),

    ('telegram_yamiarbeit',
     'Telegram 闇バイト募集(オンライン拠点・概念)',
     6, 35.6580, 139.7016, 0,
     'lore_site', '2020s', None, 'active',
     'Telegram など匿名 SNS での闇バイト募集が、2020年代のトクリュウ事件の '
     '組成基盤。物理的拠点を持たず、執行毎に異なる実行役を集める '
     '流動型組織犯罪の典型構造。',
     '解体後', '司法側'),

    ('cambodia_compounds_link',
     'カンボジア コンパウンド(トクリュウ関連海外拠点)',
     6, 11.5564, 104.9282, 5000,
     'lore_site', '2020s', None, 'active',
     'カンボジア・シハヌークビル等のコンパウンドが、'
     '日本人を含むトクリュウ系犯罪の海外指揮拠点として2020年代に注目。'
     '本マップの姉妹プロジェクト「Compound Time Machine」と直接の接続。',
     '解体後', '司法側'),

    ('hangure_tokuryu_origin_culture',
     '半グレ起源 — 暴走族から不良へ',
     6, 35.6580, 139.7016, 1500,
     'lore_site', '1990s', None, 'historical',
     '関東連合・怒羅権など半グレの起源は、1980-90年代の暴走族・地元不良グループ。'
     '暴対法による指定暴力団への参入路が狭まった結果、'
     '組織化されないまま組織犯罪に近接する若者層が形成された経路。',
     '高度成長', '司法側'),

    ('shinjuku_chaika_hangure',
     '新宿チャイカ — 半グレ系飲食店事件(2010s)',
     6, 35.6938, 139.7034, 200,
     'attack_site', '2010s', None, 'historical',
     '新宿歌舞伎町の飲食店「チャイカ」など、半グレ系の事件が複数報じられた場所。'
     '指定暴力団の縄張りと半グレの活動エリアが重なる典型事例。',
     '平成抗争', '司法側'),

    ('shibuya_halloween_arrest',
     '渋谷 — ハロウィン暴徒化と半グレ',
     6, 35.6595, 139.7000, 200,
     'lore_site', '2018', None, 'active',
     '2018年のハロウィン渋谷で軽トラック横転事件など、'
     '半グレ系若者の組織的暴徒化が問題化。'
     '警察庁の「準暴力団」運用の対象として議論された事案群。',
     '解体後', '司法側'),

    ('special_fraud_callcenter',
     '特殊詐欺コールセンター(国内・海外)',
     6, 35.7100, 139.7700, 5000,
     'lore_site', '2010s', None, 'active',
     '特殊詐欺(オレオレ詐欺・還付金詐欺など)のコールセンターは '
     '国内・海外(タイ・カンボジア・フィリピン)に拡散。'
     '指定暴力団資金源だった2010年代から、トクリュウ型独立組成への変容期。',
     '解体後', '司法側'),

    ('hangure_yokohama_chinatown',
     '横浜中華街 — チャイニーズ系半グレ',
     6, 35.4437, 139.6463, 400,
     'lore_site', '2000s', None, 'active',
     '横浜中華街周辺は怒羅権など中国系半グレの活動エリアの一つとして報道された。'
     '伝統的中華街文化と現代型組織犯罪の交わる地域。',
     '平成抗争', '司法側'),

    # ===== トクリュウ 個別事案(地理的拡散)=====
    ('inagi_robbery_2022',
     '稲城市 高齢者強盗(2022 前兆事案)',
     6, 35.6383, 139.5043, 400,
     'attack_site', '2022', '2022', 'historical',
     '東京都稲城市で発生した高齢者宅強盗事件。'
     '2023年の連続強盗の前兆事案として後に位置づけられた。',
     '解体後', '司法側'),

    ('chiba_isumi_robbery',
     '千葉県内 連続強盗(2023)',
     6, 35.6073, 140.1227, 5000,
     'attack_site', '2023', '2024', 'historical',
     '千葉県内で2023年以降に発生した連続強盗事件。'
     '高齢者宅・店舗を狙ったトクリュウ型犯罪が複数地域で連続。',
     '解体後', '司法側'),

    ('saitama_warabi_robbery',
     '埼玉県 蕨市 連続強盗(2023)',
     6, 35.8259, 139.6802, 400,
     'attack_site', '2023', '2023', 'historical',
     '埼玉県蕨市で発生したトクリュウ系強盗事件。'
     '高齢者宅を狙った典型的な闇バイト型犯行。',
     '解体後', '司法側'),

    ('ibaraki_chikusei_robbery',
     '茨城県 筑西市 強盗(2023)',
     6, 36.3070, 139.9831, 400,
     'attack_site', '2023', '2023', 'historical',
     '茨城県筑西市の高齢者宅強盗事件。'
     '関東広域連続強盗の北端の発生地。',
     '解体後', '司法側'),

    ('tochigi_oyama_robbery',
     '栃木県 小山市 強盗(2023)',
     6, 36.3147, 139.8003, 400,
     'attack_site', '2023', '2023', 'historical',
     '栃木県小山市の連続強盗事件。'
     '北関東に拡散したトクリュウ型犯行の代表事例。',
     '解体後', '司法側'),

    ('kanagawa_yokohama_robbery',
     '神奈川県 横浜市 強盗(2023-2024)',
     6, 35.4437, 139.6380, 2000,
     'attack_site', '2023', '2024', 'historical',
     '神奈川県横浜市内で発生した複数の強盗事件。'
     '都市部の高齢者宅・店舗を狙うトクリュウ型犯行が連続。',
     '解体後', '司法側'),

    ('osaka_robbery_tokuryu',
     '大阪府内 強盗事件(2023-2024)',
     6, 34.6937, 135.5023, 3000,
     'attack_site', '2023', '2024', 'historical',
     '大阪府内でも2023-2024年にトクリュウ型強盗事件が報じられた。'
     '関西への地理的拡散として注目された。',
     '解体後', '司法側'),

    ('aichi_nagoya_robbery',
     '愛知県 名古屋市 強盗(2023-2024)',
     6, 35.1815, 136.9066, 2000,
     'attack_site', '2023', '2024', 'historical',
     '愛知県名古屋市内のトクリュウ型強盗事件。'
     '中部圏への広域拡散の代表事例。',
     '解体後', '司法側'),

    ('hyogo_robbery_2024',
     '兵庫県 神戸市 強盗(2024)',
     6, 34.6900, 135.1800, 2000,
     'attack_site', '2024', '2024', 'historical',
     '兵庫県神戸市内で2024年に発生したトクリュウ型強盗事件。'
     '関西圏でも継続的に拡散していることを示す事例。',
     '解体後', '司法側'),

    ('fukuoka_robbery_2024',
     '福岡県内 強盗事件(2024)',
     1, 33.5879, 130.4172, 5000,
     'attack_site', '2024', '2024', 'historical',
     '福岡県内のトクリュウ型強盗事件。'
     '工藤會解体後の九州にも現代型組織犯罪が及んだ事例。',
     '解体後', '司法側'),

    ('takasaki_gunma_robbery',
     '群馬県 高崎市 強盗(2023)',
     6, 36.3220, 138.9978, 500,
     'attack_site', '2023', '2023', 'historical',
     '群馬県高崎市内の強盗事件。北関東への拡散事例。',
     '解体後', '司法側'),

    ('niigata_robbery_2024',
     '新潟県内 強盗(2024)',
     6, 37.9026, 139.0234, 5000,
     'attack_site', '2024', '2024', 'historical',
     '新潟県内のトクリュウ型強盗事件。'
     '太平洋側以外への拡散の一例。',
     '解体後', '司法側'),

    # ===== SNS リクルーター摘発 =====
    ('tokyo_sns_recruiter_office',
     'SNS リクルーター摘発拠点(東京)',
     6, 35.6580, 139.7016, 3000,
     'attack_site', '2024', None, 'historical',
     '2024年以降に摘発された SNS 経由の闇バイト募集側拠点(複数)。'
     '東京を中心に募集投稿の作成・発信が行われていた。',
     '解体後', '司法側'),

    ('osaka_sns_recruiter',
     'SNS リクルーター摘発拠点(大阪)',
     6, 34.6937, 135.5023, 3000,
     'attack_site', '2024', None, 'historical',
     '関西でも闇バイト募集側の摘発事案が継続。'
     '指示役と募集役の分離構造が示された。',
     '解体後', '司法側'),

    ('ulu_atm_demand',
     'ATM 受け子・出し子の連続摘発',
     6, 35.6760, 139.6503, 5000,
     'attack_site', '2020s', None, 'active',
     '特殊詐欺・トクリュウ事件で ATM での現金引き出し役(出し子)・'
     '受け取り役(受け子)の摘発が連続。実行役の若年層への広がりが社会問題化。',
     '解体後', '司法側'),

    ('roman_sagi_online',
     'ロマンス詐欺 — SNS 経由の組織化',
     6, 35.6760, 139.6503, 5000,
     'lore_site', '2018', None, 'active',
     'マッチングアプリ・SNS 経由のロマンス詐欺が2018年以降組織化。'
     'トクリュウ型の海外拠点+国内実行役の構図が広がる。'
     '被害額は年間100億円規模に達する報告も。',
     '解体後', '司法側'),

    ('kanto_rengo_ob_network',
     '関東連合 OB ネットワーク',
     6, 35.6630, 139.7325, 1500,
     'lore_site', '2014', None, 'active',
     '関東連合解散(2014)後、元メンバーは個別のビジネス・人脈で活動継続。'
     '一部は実業界・芸能界に進出、一部は指定暴力団系列へ合流、'
     '一部は新型組織犯罪の指示役に転じたと報じられた。',
     '解体後', '半グレ'),

    ('ex_yakuza_to_tokuryu',
     '元組員のトクリュウ流入事案',
     6, 35.7100, 139.7700, 5000,
     'lore_site', '2020s', None, 'active',
     '指定暴力団離脱者の一部がトクリュウ型犯罪の指示役・組成役として '
     '関与する事案が複数報じられた。'
     '組織犯罪の人材が伝統型から流動型へ移行する構図。',
     '解体後', 'トクリュウ'),

    # ===== 他地域 =====
    ('okinawa_kyokuryukai_main',
     '旭琉会 本部(沖縄県・那覇)',
     6, 26.2123, 127.6792, 200,
     'hq_current', '1949', None, 'active',
     '沖縄県那覇市に本拠を置く指定暴力団 旭琉会。'
     '1949年起源、米軍統治・1972年本土復帰の特殊な歴史背景。'
     '全国の指定暴力団の中でも極めて独自の発展経路を持つ。',
     '戦後闇市', '司法側'),

    ('okinawa_us_military_yakuza',
     '沖縄米軍基地周辺(基地周辺ヤクザ史)',
     6, 26.3344, 127.8056, 5000,
     'lore_site', '1950s', None, 'active',
     '沖縄の米軍基地周辺は、米軍統治時代から独特のヤクザ文化が発達。'
     '基地周辺の歓楽街・物資ヤミ取引・米兵相手の事業など、'
     '本土とは異なる経済構造が組織犯罪の母体となった。',
     '戦後闇市', '司法側'),

    ('koza_okinawa',
     'コザ(沖縄市)— 米軍基地と組',
     6, 26.3344, 127.8056, 1500,
     'district', '1950s', None, 'active',
     '沖縄市(旧コザ市)は米軍嘉手納基地周辺の歓楽街。'
     '本土復帰前後のヤクザ史の中心地として報道書籍に頻出。',
     '戦後闇市', '司法側'),

    ('kyoto_aizukotetsu_hq',
     '会津小鉄会 本部(京都)',
     6, 35.0036, 135.7681, 200,
     'hq_current', '1869', None, 'active',
     '京都市内の指定暴力団 会津小鉄会 本部。1869年起源と日本最古級。'
     '関西地場連合体として、九州・関東とは別系統で発展。',
     '戦後闇市', '司法側'),

    ('kyoto_gion',
     '祇園(京都)— 伝統花街と組',
     6, 35.0036, 135.7752, 400,
     'district', '1700s', None, 'active',
     '京都の祇園は江戸時代からの伝統花街。'
     '会津小鉄会など関西地場ヤクザの活動エリアの一つで、'
     '伝統文化と現代の組織犯罪規制が交わる場所。',
     '高度成長', '司法側'),

    ('nagoya_kodokai_hq',
     '弘道会 本部(名古屋・愛知)',
     6, 35.1815, 136.9066, 200,
     'hq_current', '1984', None, 'active',
     '名古屋市内の弘道会。六代目山口組の最大2次団体で、'
     '司忍が組長を務める母体組織。日本のヤクザ史の中核組織の一つ。',
     '高度成長', '山口組系'),

    ('nagoya_sakae_district',
     '名古屋 栄(中部最大歓楽街)',
     6, 35.1700, 136.9080, 400,
     'district', '1950s', None, 'active',
     '名古屋市中区栄。中部地方最大の歓楽街で、'
     '弘道会・複数組織の縄張りが交錯した中部組織犯罪史の中心地。',
     '高度成長', '山口組系'),

    ('osaka_minami_yakuza',
     '大阪ミナミ — 関西地場ヤクザ集中地',
     6, 34.6680, 135.5020, 600,
     'district', '1950s', None, 'active',
     '大阪市中央区ミナミ(難波・道頓堀周辺)。関西最大の歓楽街で、'
     '山口組系・酒梅組・複数地場組織の縄張りが集中。',
     '高度成長', '山口組系'),

    ('osaka_kita_yakuza',
     '大阪キタ(梅田)— ビジネス街と組',
     6, 34.7024, 135.4959, 600,
     'district', '1950s', None, 'active',
     '大阪市北区(梅田・北新地)。関西経済の中枢で、'
     '山口組系の経済活動の拠点でもあった。',
     '高度成長', '山口組系'),

    ('osaka_kamagasaki',
     '大阪 釜ヶ崎(あいりん地区)— 日雇い労働者街',
     6, 34.6500, 135.5050, 500,
     'lore_site', '1960s', None, 'active',
     '大阪市西成区の釜ヶ崎(あいりん地区)。日本最大級の日雇い労働者街。'
     '戦後の労働者文化と組織犯罪の交点として、'
     '戦後ヤクザ史研究の重要な参照点。',
     '高度成長', '市民側'),

    # ===== テーマ層: 経済ヤクザ・政治 =====
    ('kobe_geinosha',
     '神戸芸能社(1957設立・興行)',
     6, 34.6900, 135.1850, 300,
     'lore_site', '1957', '1989', 'historical',
     '1957年、三代目山口組組長 田岡一雄が設立した芸能興行会社。'
     '美空ひばり・北島三郎ら戦後歌謡界の主要歌手の興行を担い、'
     'ヤクザと芸能界の戦後の関係の象徴。'
     '1989年解散、後の暴排運動で芸能界とヤクザの分離が進んだ起点。',
     '高度成長', '山口組系'),

    ('kodama_yoshio_residence',
     '児玉誉士夫 関連拠点(東京)',
     6, 35.6580, 139.7016, 1500,
     'lore_site', '1950s', '1984', 'historical',
     '児玉誉士夫(1911-1984)は戦後の右翼・フィクサー。'
     '東京・赤坂を拠点に政界・財界・ヤクザ社会を結ぶ役割を果たした。'
     '1976年ロッキード事件で関与が明らかに。',
     '高度成長', '司法側'),

    ('lockheed_scandal',
     'ロッキード事件 関連(1976-)',
     6, 35.6757, 139.7560, 100,
     'lore_site', '1976-02', '1983', 'historical',
     '1976年2月、米上院公聴会で発覚したロッキード社の航空機販売贈賄事件。'
     '田中角栄元首相が逮捕、児玉誉士夫の関与で戦後ヤクザと政界の関係が '
     '国際的に注目された事件。',
     '高度成長', '司法側'),

    ('bubble_jiage',
     'バブル期 地上げ事案ライン(1985-1991)',
     6, 35.6580, 139.7016, 5000,
     'lore_site', '1985', '1991', 'historical',
     '1980年代後半のバブル期、東京都心の地上げに住吉会・稲川会・山口組系の '
     '関与が広範に報じられた。'
     '住民立ち退き・強迫・暴力沙汰が社会問題化、後の暴対法(1991)の主要背景の一つ。',
     '高度成長', '司法側'),

    ('jusen_jutaku',
     '住宅金融専門会社(住専)— 1995-1996',
     6, 35.6814, 139.7670, 200,
     'lore_site', '1995', '1996', 'historical',
     '1995年の住専問題は、バブル期の不良債権処理で表面化した経済事案。'
     '住専の貸付先にヤクザ系企業が含まれていた事実が国会・報道で議論された。'
     '6850億円の公的資金投入で社会問題化。',
     '頂上作戦', '司法側'),

    ('kansai_quake_yamaguchi',
     '阪神・淡路大震災と山口組(1995-01-17)',
     6, 34.7000, 135.2000, 500,
     'lore_site', '1995-01-17', '1995-02', 'historical',
     '1995年1月17日の阪神・淡路大震災で、神戸の六代目山口組(当時五代目)が '
     '本部前で被災者支援(炊き出し・物資配給)を行った事実は広く報道された。'
     'ヤクザの社会的役割をめぐる議論の重要な事例。',
     '高度成長', '山口組系'),

    # ===== テーマ層: スポーツ・芸能 =====
    ('proyakyu_kuroikiri',
     'プロ野球「黒い霧事件」(1969-1971)',
     6, 35.7090, 139.7170, 200,
     'lore_site', '1969', '1971', 'historical',
     '1969-1971年、プロ野球選手の八百長・賭博関与が次々と発覚した「黒い霧事件」。'
     '永易将之投手の告発を発端に、複数選手が永久追放処分。'
     '指定暴力団との関係が組織的に表面化した戦後スポーツ史最大の事件。',
     '高度成長', '司法側'),

    ('sumo_yakyu_baqto',
     '大相撲 野球賭博事件(2010)',
     6, 35.7066, 139.7945, 200,
     'lore_site', '2010-05', '2010-08', 'historical',
     '2010年5月、大相撲力士・親方の野球賭博関与が報道で発覚。'
     '指定暴力団との資金関係が明らかになり、'
     '日本相撲協会は名古屋場所中止寸前まで追い込まれた。'
     '複数力士の解雇・親方の引退処分。',
     '頂上作戦', '司法側'),

    ('sumo_yaocho_2011',
     '大相撲 八百長問題(2011)',
     6, 35.7066, 139.7945, 200,
     'lore_site', '2011-02', '2011-04', 'historical',
     '2011年2月、メール記録から大相撲の八百長関与が報道で発覚。'
     '前年の野球賭博事件と続き、相撲協会の暴排態勢の整備が進んだ。'
     '本場所中止、複数力士の処分。',
     '頂上作戦', '司法側'),

    # ===== テーマ層: 薬物経済 =====
    ('drug_smuggling_routes',
     '覚せい剤 国際密輸ルート(戦後-)',
     6, 35.7000, 139.7700, 5000,
     'lore_site', '1950s', None, 'active',
     '日本の覚せい剤密輸の主要ルートは韓国・北朝鮮・中国・東南アジアを経由。'
     '指定暴力団各組織が国内流通を担ってきた歴史。'
     '2020年代以降は半グレ・トクリュウ系の流通も報じられた。',
     '高度成長', '司法側'),

    ('drug_busts_1990s',
     '覚せい剤 大規模摘発事案(1990s-)',
     6, 35.7100, 139.7700, 2000,
     'attack_site', '1990s', None, 'active',
     '1990年代以降、指定暴力団系の覚せい剤大規模摘発事案が複数発生。'
     '海上保安庁・税関の国際密輸摘発が継続的に報じられた。',
     '平成抗争', '司法側'),

    # ===== テーマ層: 戦後初期の抗争 =====
    ('honda_kai_war',
     '本多会・山口組抗争(1960年代前半)',
     6, 34.7000, 135.1900, 800,
     'attack_site', '1960', '1965', 'historical',
     '1960年代前半、関西で山口組と本多会の抗争。'
     '田岡一雄時代の山口組が関西統一を進める中で発生した大規模抗争。'
     '一般市民への被害も発生した。',
     '高度成長', '山口組系'),

    ('postwar_sanguokujin',
     '戦後混乱期 三国人事件(1946-1950)',
     6, 35.6938, 139.7034, 1500,
     'lore_site', '1946', '1950', 'historical',
     '戦後直後の闇市における朝鮮人・台湾人など「三国人」集団と日本人テキ屋系の衝突。'
     '関東・関西・九州で複数の事案が報じられた、戦後ヤクザ史の重要な前史。',
     '戦後闇市', '司法側'),

    # ===== テーマ層: 興行 =====
    ('misora_hibari_taoka',
     '美空ひばりと田岡一雄(神戸芸能社時代)',
     6, 34.6900, 135.1850, 300,
     'lore_site', '1957', '1989', 'historical',
     '美空ひばりは神戸芸能社所属時代(1957-1989)、田岡一雄と「親子の盃」を交わしたとされる。'
     '1989年の田岡長女死去をきっかけに芸能界と山口組の正式な分離が進んだ。',
     '高度成長', '山口組系'),

    ('koshienjo_yakuza',
     '甲子園歌謡ショー(1960s)',
     6, 34.7212, 135.3611, 300,
     'lore_site', '1960s', None, 'historical',
     '1960年代、甲子園球場での歌謡ショーは神戸芸能社の主要興行の一つ。'
     '戦後芸能界の興行と山口組の関係の典型事例。',
     '高度成長', '山口組系'),

    # ===== 薬物経済 深掘り拠点 =====
    ('hiropon_first_wave',
     '第一次覚せい剤流行 — ヒロポン時代(1945-1955)',
     6, 35.6938, 139.7034, 3000,
     'lore_site', '1945', '1955', 'historical',
     '戦後直後、軍事用備蓄の覚せい剤(ヒロポン)が市場に流出。'
     '戦後復興期の労働者・労組・闇市文化と結びついて第一次流行を形成。'
     '1951年覚せい剤取締法成立、1955年頃まで断続的に蔓延。',
     '戦後闇市', '司法側'),

    ('hiropon_second_wave',
     '第二次覚せい剤流行(1970年代後半-1980年代)',
     6, 35.6938, 139.7034, 3000,
     'lore_site', '1975', '1985', 'historical',
     '1970年代後半から1980年代にかけての第二次覚せい剤流行。'
     '山口組系・住吉会系など指定暴力団が国内流通を本格的に組織化。'
     '韓国・台湾・香港経由の密輸ルートが確立した時期。',
     '高度成長', '司法側'),

    ('iranian_dealers_shibuya',
     'イラン人売人問題 — 渋谷・新宿(1990s)',
     6, 35.6595, 139.7000, 800,
     'attack_site', '1990s', '2000s', 'historical',
     '1990年代、渋谷・新宿・池袋でイラン人売人による路上薬物販売が問題化。'
     '指定暴力団とは別系統の組織犯罪の代表事例として警察庁の対策対象に。',
     '平成抗争', '司法側'),

    ('cannabis_route_history',
     '大麻 流通ルート(1990s-)',
     6, 35.6938, 139.7034, 3000,
     'lore_site', '1990s', None, 'active',
     '日本の大麻流通は1990年代以降拡大。'
     '指定暴力団系・半グレ系・個人輸入の3系統が並存する構造に。'
     '2020年代以降は SNS 経由の小規模取引が増加。',
     '頂上作戦', '司法側'),

    ('dangerous_drugs_zone',
     '危険ドラッグ(脱法ドラッグ)— 池袋・渋谷',
     6, 35.7295, 139.7109, 800,
     'attack_site', '2010', '2014', 'historical',
     '2010-2014年、脱法ドラッグ(後に「危険ドラッグ」改称)が '
     '池袋・渋谷で大規模に流通。'
     '吸引運転事故が連続発生、社会問題化。'
     '2014年薬機法改正で規制強化、店舗摘発が進む。',
     '頂上作戦', '司法側'),

    ('drug_telegram_market',
     'Telegram 薬物取引 — オンライン闇市場',
     6, 35.6938, 139.7034, 0,
     'lore_site', '2020', None, 'active',
     '2020年代、Telegram・X(旧Twitter)などの SNS 経由の薬物取引が拡大。'
     '指定暴力団・半グレ・トクリュウ・個人売買が混在する '
     'オンライン闇市場の形成。'
     '従来の街頭密売と異なる流通構造。',
     '解体後', 'トクリュウ'),

    ('drug_korea_route',
     '薬物密輸 韓国・北朝鮮ルート',
     6, 35.5494, 129.3114, 50000,
     'lore_site', '1970s', None, 'active',
     '韓国・北朝鮮を経由する覚せい剤密輸は戦後日本の主要ルートの一つ。'
     '海上船便・空港・コンテナ密輸が継続的に摘発された。',
     '高度成長', '司法側'),

    ('drug_china_southeast',
     '薬物密輸 中国・東南アジアルート',
     6, 13.7563, 100.5018, 50000,
     'lore_site', '1990s', None, 'active',
     '中国本土・タイ・カンボジア・ベトナム経由の薬物密輸ルート。'
     'ゴールデントライアングルからの伝統的流通と、'
     '現代のメコンコンパウンドからの流通が並存。',
     '平成抗争', '司法側'),

    ('drug_meth_2019_yokohama',
     '横浜港 大規模覚せい剤押収事案(2019)',
     6, 35.4437, 139.6463, 1000,
     'attack_site', '2019', '2019', 'historical',
     '2019年、横浜港でコンテナ輸送の大規模覚せい剤(数百キロ規模)が押収。'
     '海上保安庁・税関・警察の合同摘発として全国的に報じられた。'
     '指定暴力団系の国際密輸ネットワークの摘発事例。',
     '頂上作戦', '司法側'),

    ('drug_2020s_busts',
     '2020年代 大規模薬物摘発(継続)',
     6, 35.6938, 139.7034, 5000,
     'attack_site', '2020', None, 'active',
     '2020年代以降も大規模薬物摘発が継続。'
     'コロナ禍以降の国際物流変化で密輸経路が複雑化。'
     '指定暴力団・トクリュウ系・半グレ系の流通が混在する状況。',
     '解体後', '司法側'),

    # ===== トクリュウ 深掘り拠点 =====
    ('luffy_court_proceedings',
     'ルフィ事件 公判(東京地裁)',
     6, 35.6757, 139.7560, 200,
     'lore_site', '2023', None, 'active',
     '東京地方裁判所で進行中のルフィ事件関連被告(渡邊優樹ら)の公判。'
     '指示役と実行役の関係立証、SNS 証拠の刑事法的扱いが争点。'
     'トクリュウ型犯罪の司法的位置づけのパイロットケース。',
     '解体後', '司法側'),

    ('luffy_satsumitsu_court',
     'ルフィ事件 — 殺人罪判決(被告ら)',
     6, 35.6757, 139.7560, 200,
     'ruling', '2024', None, 'active',
     'ルフィ事件関連被告に対する殺人罪・強盗殺人罪の判決進行中。'
     '量刑は無期懲役以上が想定されており、'
     '指示役4人の責任配分が刑事司法の論点。',
     '解体後', '司法側'),

    ('tokuryu_recruiter_takedown',
     'SNS リクルーター 大規模摘発(2024-)',
     6, 35.6580, 139.7016, 3000,
     'attack_site', '2024', None, 'active',
     '2024年以降の警察庁・各都道府県警によるSNS闇バイト募集側の大規模摘発。'
     '指示役・募集役・実行役の連鎖切断戦略の典型事例。',
     '解体後', 'トクリュウ'),

    ('tokuryu_crypto_laundering',
     'トクリュウ 仮想通貨マネロン経路',
     6, 35.6580, 139.7016, 0,
     'lore_site', '2020', None, 'active',
     'トクリュウ事件の資金流通で仮想通貨(暗号資産)を介したマネロン経路が報じられた。'
     '従来の現金ベースから、SNS 募集 → 仮想通貨送金 → 海外換金 の '
     '新型流通構造への変化。',
     '解体後', 'トクリュウ'),

    ('myanmar_compounds_link',
     'ミャンマー国境コンパウンド(SS 直接接続)',
     6, 16.6890, 98.2680, 5000,
     'lore_site', '2018', None, 'active',
     'ミャンマー・タイ国境の詐欺コンパウンド群。'
     '日本人を含むトクリュウ型犯罪の指示拠点として2022年以降注目された。'
     '本マップの姉妹プロジェクト「Compound Time Machine」が詳細を扱う。',
     '解体後', 'トクリュウ'),

    ('thailand_tokuryu_base',
     'タイ拠点 — 日本人指示役',
     6, 13.7563, 100.5018, 3000,
     'lore_site', '2022', None, 'active',
     'タイ・バンコク・パタヤなど東南アジア各地で、'
     '日本人指示役が活動拠点を移すケースが報じられた。'
     'フィリピン入管摘発(ルフィ事件)後の指示役分散化の動き。',
     '解体後', 'トクリュウ'),

    ('jr_route_robbery_2024',
     'JR 路線沿線 連続強盗(2024)',
     6, 35.6760, 139.6503, 5000,
     'attack_site', '2024', None, 'active',
     '2024年、JR 主要路線沿線(中央線・常磐線・武蔵野線等)での '
     '連続強盗事件。アクセスのよさが標的選定の基準になった可能性。',
     '解体後', 'トクリュウ'),

    ('tokuryu_young_recruits',
     'トクリュウ実行役 — 若年層問題',
     6, 35.7100, 139.7700, 3000,
     'lore_site', '2023', None, 'active',
     '2023-2024 連続強盗事件で逮捕された実行役には大学生・高校生・10代の '
     '若者が多く含まれた。学校・自治体での予防啓発が急増。',
     '解体後', 'トクリュウ'),

    ('tokuryu_pawn_jewelry_route',
     '宝石店・質店襲撃ルート(2023-2024)',
     6, 35.6580, 139.7016, 5000,
     'attack_site', '2023', '2024', 'historical',
     '宝石店・質店・両替店への襲撃事件は、現金保管の小規模店舗を狙う '
     'トクリュウ型犯行の典型。昼間の都心商業地での襲撃が衝撃を呼んだ。',
     '解体後', 'トクリュウ'),

    ('roman_sagi_centers',
     'ロマンス詐欺 — 国際拠点(複数)',
     6, 13.7563, 100.5018, 5000,
     'lore_site', '2018', None, 'active',
     'マッチングアプリ・SNS 経由のロマンス詐欺は国際的組成。'
     'タイ・カンボジア・ナイジェリア・ガーナなどに拠点を持つ複数組織が日本人を狙う。'
     '被害額は年間100億円規模に達した報告も。',
     '解体後', 'トクリュウ'),

    ('atm_uketakedashi_arrests',
     'ATM 出し子・受け子 連続逮捕(2020s)',
     6, 35.6580, 139.7016, 5000,
     'attack_site', '2020', None, 'active',
     '特殊詐欺・トクリュウ事件の ATM 現金引き出し役(出し子)・受け取り役(受け子)の '
     '連続逮捕。若年層の関与が社会問題化、'
     '銀行業界の ATM 監視強化と並行する動き。',
     '解体後', 'トクリュウ'),

    ('school_predator_warning',
     '学校・自治体 闇バイト予防啓発(2024-)',
     6, 35.6580, 139.7016, 3000,
     'lore_site', '2024', None, 'active',
     '2024年以降、全国の学校・自治体で闇バイト予防啓発が急速に拡大。'
     'SNS 上の「ホワイトな高額バイト」募集が若者を狙う構図への警告。',
     '解体後', '市民側'),

    ('tokuryu_kankoku_link',
     '韓国系トクリュウ — 国際的接続',
     6, 35.5494, 129.3114, 5000,
     'lore_site', '2020', None, 'active',
     '韓国系の指示役・実行役の関与が報じられた事案。'
     '日韓越境の組織犯罪として継続的に注目される。',
     '解体後', 'トクリュウ'),

    # ===== 北海道 =====
    ('sapporo_susukino',
     '札幌 すすきの — 北海道最大の歓楽街',
     6, 43.0567, 141.3530, 500,
     'district', '1950s', None, 'active',
     '札幌市中央区 すすきの。東京の歌舞伎町・大阪のミナミと並ぶ '
     '日本三大歓楽街の一つ。'
     '指定暴力団・山口組系列の進出地・地場組織の活動エリアとして報道。'
     '暴対法施行(1992)以降、暴排運動が継続。',
     '高度成長', '司法側'),

    ('hokkaido_keisatsu',
     '北海道警察本部',
     6, 43.0658, 141.3477, 100,
     'landmark', None, None, 'active',
     '札幌市中央区 — 北海道警察本部。'
     '北海道は山口組系列の進出地として継続的な対応が必要な地域。'
     '面積最大の県警として広域管轄。',
     '頂上作戦', '県警側'),

    ('hakodate_chinatown',
     '函館・元町(歴史的港町)',
     6, 41.7626, 140.7287, 600,
     'district', '1850s', None, 'active',
     '函館市元町・末広町。明治期からの国際港町で、'
     '戦後ヤクザ史にも独自の発展経路を持つ地域。'
     '小樽・函館の港町文化と組織犯罪の関係は北海道ヤクザ史研究で言及される。',
     '戦後闇市', '司法側'),

    ('otaru_yakuza_history',
     '小樽・運河エリア(港湾労働者街)',
     6, 43.1980, 140.9942, 600,
     'lore_site', '1950s', None, 'active',
     '小樽市の運河沿い・色内エリアは戦後港湾労働者街。'
     '戦後闇市文化と組織犯罪の交点として、北海道ヤクザ史の前史。',
     '戦後闇市', '司法側'),

    # ===== 東北 =====
    ('sendai_kokubun',
     '仙台 国分町 — 東北最大の歓楽街',
     6, 38.2618, 140.8744, 400,
     'district', '1950s', None, 'active',
     '仙台市青葉区 国分町。東北最大の歓楽街(約2000店舗)。'
     '指定暴力団・地場組織の活動エリアとして継続的に報道される。'
     '2011年東日本大震災後の復興期に暴排運動が大幅に強化。',
     '高度成長', '司法側'),

    ('sendai_station_area',
     '仙台駅周辺',
     6, 38.2606, 140.8821, 200,
     'landmark', None, None, 'active',
     '仙台市青葉区中央 — 東北最大のターミナル駅。'
     '東北新幹線停車駅で、東北6県の交通結節点。',
     '高度成長', '市民側'),

    ('miyagi_keisatsu',
     '宮城県警察本部',
     6, 38.2685, 140.8723, 100,
     'landmark', None, None, 'active',
     '仙台市青葉区 — 宮城県警察本部。'
     '東北の指定暴力団情勢への対応・東日本大震災後の暴排運動の主軸。',
     '頂上作戦', '県警側'),

    ('koriyama_fukushima_renge',
     '郡山 — 福島連合 本拠地',
     6, 37.4006, 140.3593, 800,
     'hq_current', '1990s', None, 'active',
     '福島県郡山市 — 福島連合(指定暴力団)の本拠地として報道された地域。'
     '東北で唯一の指定暴力団系統。'
     '2011年東日本大震災・福島第一原発事故の影響を強く受けた地域。',
     '平成抗争', '司法側'),

    ('fukushima_keisatsu',
     '福島県警察本部',
     6, 37.7503, 140.4675, 100,
     'landmark', None, None, 'active',
     '福島市 — 福島県警察本部。'
     '福島連合への継続的な対応。震災・原発事故後の復興期の暴排運動の中心。',
     '頂上作戦', '県警側'),

    # ===== 四国 =====
    ('takamatsu_marugame',
     '高松 丸亀町商店街',
     6, 34.3416, 134.0466, 300,
     'district', '1500s', None, 'active',
     '香川県高松市 丸亀町商店街(約1500m)。'
     '日本最古級のアーケード商店街で、暴排・再開発の先進事例。'
     '商店街振興組合主導の暴排運動・再開発が全国モデルとして紹介された。',
     '高度成長', '市民側'),

    ('matsuyama_bantencho',
     '松山 — 大街道・銀天街',
     6, 33.8419, 132.7656, 300,
     'district', '1950s', None, 'active',
     '松山市 — 大街道・銀天街は四国最大級の商業地。'
     '四国地場の指定暴力団系列の活動エリアとして継続的に報道。',
     '高度成長', '司法側'),

    ('kagawa_keisatsu',
     '香川県警察本部 + 四国管区警察局',
     6, 34.3401, 134.0436, 100,
     'landmark', None, None, 'active',
     '高松市 — 香川県警本部 + 四国管区警察局。'
     '四国4県の組織犯罪情勢の中央集約地。',
     '頂上作戦', '県警側'),

    ('shikoku_yakuza_landscape',
     '四国地場ヤクザ史 — 山口組系の進出',
     6, 33.7500, 133.5000, 100000,
     'lore_site', '1980s', None, 'active',
     '四国4県は1980年代以降の山口組系列の進出地として知られる。'
     '地場連合体と山口組系の縄張りが交錯し、'
     '各県警が継続的な対応を続ける地域。',
     '高度成長', '山口組系'),

    # ===== 北陸 =====
    ('niigata_furumachi',
     '新潟 古町 — 日本海側最大の歓楽街',
     6, 37.9159, 139.0364, 400,
     'district', '1700s', None, 'active',
     '新潟市中央区 古町 — 日本海側最大の歓楽街。'
     '江戸時代の港町文化から発展。指定暴力団系列の活動エリア。',
     '高度成長', '司法側'),

    ('kanazawa_katamachi',
     '金沢 香林坊・片町',
     6, 36.5601, 136.6553, 400,
     'district', '1950s', None, 'active',
     '金沢市 香林坊・片町は北陸最大級の歓楽街。'
     '指定暴力団・山口組系列の進出地として知られる。',
     '高度成長', '司法側'),

    ('toyama_keisatsu_area',
     '富山県警 + 北陸ヤクザ史',
     6, 36.6953, 137.2113, 300,
     'landmark', None, None, 'active',
     '富山市 — 富山県警本部周辺。'
     '北陸三県(富山・石川・福井)の組織犯罪情勢への対応。',
     '頂上作戦', '県警側'),

    # ===== その他 =====
    ('niigata_chuetsu_jishin',
     '新潟県中越地震(2004)と暴排運動',
     6, 37.3026, 138.8814, 5000,
     'lore_site', '2004-10-23', None, 'active',
     '2004年10月23日の中越地震・2007年中越沖地震を経て、'
     '新潟県内の災害復興と暴排運動が並走した経緯。'
     '災害便乗の不当業者への警戒が地域住民レベルで定着した。',
     '平成抗争', '市民側'),

    ('disaster_311_yakuza_response',
     '東日本大震災(2011)と暴排運動',
     6, 38.2606, 140.8821, 10000,
     'lore_site', '2011-03-11', None, 'active',
     '2011年3月11日の東日本大震災・福島第一原発事故。'
     '災害便乗の不当業者(瓦礫処理・除染関連)への警戒が東北全域で強化。'
     '警察庁・福島県警は復興事業から指定暴力団系企業を排除する '
     '専門チームを組織した。',
     '頂上作戦', '司法側'),
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
