"""Render index.html from kokura.db — entertainment-oriented version.

Surfaces every layer (sites, events, lore, chronicle, prosecutions, testimony,
local life, Wayback frames, POIs) and color-codes everything by three modes:
  - kind     (event type)
  - faction  (派閥: 工藤會 / 草野一家系 / 工藤組系 / 山口組系 / 道仁会系 /
              県警側 / 司法側 / 市民側 / 田中組系)
  - era      (戦後闇市 / 高度成長 / 平成抗争 / 頂上作戦 / 解体後)

Lore cards (gossip layer) get gold trim. Severity drives marker size.
"""
from __future__ import annotations
import datetime, json, os, sqlite3


HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')
OUT_HTML = os.path.join(HERE, 'index.html')


# ---------- Palettes ----------
FACTION_PALETTE = {
    '工藤會':       '#d9534f',
    '草野一家系':   '#c0392b',
    '工藤組系':     '#e67e22',
    '田中組系':     '#f39c12',
    '山口組系':     '#8e44ad',
    '道仁会系':     '#9b59b6',
    '福博会系':     '#7d3c98',
    '半グレ':       '#ff6b35',
    'トクリュウ':   '#ff1744',
    '中国系':       '#ffb300',
    '県警側':       '#2980b9',
    '司法側':       '#16a085',
    '市民側':       '#27ae60',
    '著作者':       '#95a5a6',
}
ERA_PALETTE = {
    '戦後闇市':     '#7f8c8d',
    '高度成長':     '#3498db',
    '平成抗争':     '#c0392b',
    '頂上作戦':     '#f39c12',
    '解体後':       '#95a5a6',
}
KIND_PALETTE = {
    # event kinds
    'attack':         '#d9534f',
    'extortion':      '#e67e22',
    'arrest':         '#f39c12',
    'ruling':         '#9b59b6',
    'demolition':     '#95a5a6',
    'designation':    '#3498db',
    'war':            '#c0392b',
    'raid':           '#e74c3c',
    'faction_split':  '#8e44ad',
    'lore':           '#f1c40f',
    'death':          '#5d6d7e',
    'merger':         '#16a085',
    # site kinds (for default coloring)
    'hq_former':      '#d9534f',
    'hq_current':     '#b71c1c',
    'attack_site':    '#f5b041',
    'district':       '#3498db',
    'landmark':       '#2ecc71',
    'front':          '#9b59b6',
    'lore_site':      '#f1c40f',
}
ERA_ORDER = ['戦後闇市', '高度成長', '平成抗争', '頂上作戦', '解体後']
FACTION_ORDER = ['工藤會', '草野一家系', '工藤組系', '田中組系',
                 '山口組系', '道仁会系', '福博会系',
                 '半グレ', 'トクリュウ', '中国系',
                 '県警側', '司法側', '市民側', '著作者']

# Source-kind badges — emoji + short label + tint color. The variety here is
# the point: a glance at a card tells you whether it's grounded in court
# ruling vs. foreign press vs. documentary vs. ex-member memoir vs. film ref.
SOURCE_KIND_BADGE = {
    'news':                ('📰', '報道',         '#3498db'),
    'foreign_press':       ('🌍', '海外通信',     '#1abc9c'),
    'ruling':              ('⚖️', '判決',         '#9b59b6'),
    'official_release':    ('🏛',  '公的発表',     '#2980b9'),
    'police_whitepaper':   ('🛡',  '警察白書',     '#34495e'),
    'sanctions':           ('💵', '制裁',         '#27ae60'),
    'legislative_record':  ('🗳',  '議事録',       '#16a085'),
    'book':                ('📚', '書籍',         '#e67e22'),
    'academic':            ('🎓', '学術',         '#8e44ad'),
    'documentary':         ('🎬', 'ドキュメンタリー', '#e74c3c'),
    'film_ref':            ('🎞',  '映像参照',     '#c0392b'),
    'memoir':              ('✒️', '手記',         '#d35400'),
    'ngo':                 ('🤝', 'NPO/暴追',     '#27ae60'),
}


def has_table(cur, name: str) -> bool:
    return cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def fetch_dicts(cur, sql: str, *args) -> list[dict]:
    cur.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def leaflet_url(tmpl: str) -> str:
    return (tmpl or '').replace('{level}', '{z}').replace('{row}', '{y}').replace('{col}', '{x}')


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    HAS_EVENT     = has_table(cur, 'event')
    HAS_IMG       = has_table(cur, 'imagery_release')
    HAS_POI       = has_table(cur, 'poi')
    HAS_TESTIMONY = has_table(cur, 'testimony')
    HAS_LIFE      = has_table(cur, 'life_snippet')
    HAS_NARR      = has_table(cur, 'narration')
    HAS_ERA       = has_table(cur, 'era_caption')
    HAS_IMGRES    = has_table(cur, 'image_resource')
    HAS_LORE      = has_table(cur, 'lore')
    HAS_PERSON    = has_table(cur, 'person')
    HAS_STAT      = has_table(cur, 'crime_stat')
    HAS_ORGTREE   = has_table(cur, 'org_tree')

    sites_rows = fetch_dicts(cur, """
        SELECT s.id, s.slug, s.label, s.rep_lat AS lat, s.rep_lon AS lon,
               s.uncertainty_m AS unc, s.kind, s.first_seen, s.last_seen,
               s.status, s.notes, s.era_tag, s.faction_tag,
               p.name_canonical AS place
        FROM site s LEFT JOIN place p ON s.place_id = p.id
        ORDER BY s.id
    """)

    sites = []
    for s in sites_rows:
        sid = s['id']
        evts = []
        if HAS_EVENT:
            evts = fetch_dicts(cur, """
                SELECT e.id, e.kind, e.happened_on AS date, e.title, e.summary,
                       e.victim_role, e.weapon, e.resolution,
                       e.era_tag, e.faction_tag, e.severity,
                       src.url, src.outlet, src.title AS src_title, src.og_image,
                       src.kind AS source_kind
                FROM event e LEFT JOIN source src ON e.source_id = src.id
                WHERE e.site_id = ? ORDER BY e.happened_on
            """, sid)
        narr = []
        if HAS_NARR:
            narr = fetch_dicts(cur, "SELECT title, body FROM narration WHERE site_id=? ORDER BY ord", sid)
        eras = []
        if HAS_ERA:
            eras = fetch_dicts(cur, "SELECT year, caption FROM era_caption WHERE site_id=? ORDER BY year", sid)
        imagery = []
        if HAS_IMG:
            imagery = fetch_dicts(cur, """
                SELECT release_date AS date, tile_url AS url
                FROM imagery_release
                WHERE site_id=? AND COALESCE(is_distinct,1)=1
                ORDER BY release_date
            """, sid)
            for f in imagery:
                f['url'] = leaflet_url(f['url'])
        poi = []
        if HAS_POI:
            poi = fetch_dicts(cur, """
                SELECT lat, lon, poi_type AS type, name, descr, confidence AS conf
                FROM poi WHERE site_id=? ORDER BY poi_type
            """, sid)
        testimony = []
        if HAS_TESTIMONY:
            testimony = fetch_dicts(cur, """
                SELECT t.role, t.speaker_label, t.year, t.quote,
                       src.url AS source_url, src.outlet AS source_outlet, src.title AS source_title
                FROM testimony t LEFT JOIN source src ON t.source_id = src.id
                WHERE t.site_id = ? ORDER BY t.id
            """, sid)
        life = []
        if HAS_LIFE:
            life = fetch_dicts(cur, """
                SELECT topic, text, source_label, source_url
                FROM life_snippet WHERE site_id=? ORDER BY ord
            """, sid)
        images = []
        if HAS_IMGRES:
            images = fetch_dicts(cur, """
                SELECT local_path AS path, caption, credit, license, source_url AS src
                FROM image_resource WHERE site_id=? ORDER BY id
            """, sid)
        lore = []
        if HAS_LORE:
            lore = fetch_dicts(cur, """
                SELECT l.year_label AS year, l.title, l.body, l.spice,
                       l.era_tag, l.faction_tag,
                       src.outlet AS source_outlet, src.title AS source_title,
                       src.url AS source_url, src.kind AS source_kind
                FROM lore l LEFT JOIN source src ON l.source_id = src.id
                WHERE l.site_id = ? ORDER BY l.ord
            """, sid)
        sites.append({
            'id': sid, 'slug': s['slug'], 'label': s['label'],
            'lat': s['lat'], 'lon': s['lon'], 'unc': s['unc'],
            'kind': s['kind'], 'place': s['place'], 'status': s['status'],
            'first_seen': s['first_seen'], 'last_seen': s['last_seen'],
            'notes': s['notes'],
            'era_tag': s['era_tag'], 'faction_tag': s['faction_tag'],
            'events': evts, 'narration': narr, 'eras': eras,
            'imagery': imagery, 'poi': poi, 'testimony': testimony,
            'life': life, 'images': images, 'lore': lore,
        })

    chronicle = fetch_dicts(cur, """
        SELECT ord, year_label AS year, title, body, era_tag, faction_tag
        FROM chronicle ORDER BY ord
    """)

    prosecutions = fetch_dicts(cur, """
        SELECT ord, case_label, defendant_label, court, stage,
               decided_on, outcome, summary
        FROM prosecution ORDER BY ord
    """)

    timeline = []
    if HAS_EVENT:
        timeline = fetch_dicts(cur, """
            SELECT e.id, e.kind, e.happened_on AS date, e.title, e.summary,
                   e.victim_role, e.weapon, e.resolution,
                   e.era_tag, e.faction_tag, e.severity,
                   e.site_id, s.label AS site_label, s.slug AS site_slug,
                   src.url AS source_url, src.outlet AS source_outlet, src.og_image,
                   src.kind AS source_kind
            FROM event e
                 LEFT JOIN site s ON e.site_id = s.id
                 LEFT JOIN source src ON e.source_id = src.id
            ORDER BY e.happened_on
        """)

    # Top-spice lore items for the side panel drawer (regardless of site
    # anchor) — these are the "highlight reel" entries.
    floating_lore = []
    if HAS_LORE:
        floating_lore = fetch_dicts(cur, """
            SELECT l.year_label AS year, l.title, l.body, l.spice,
                   l.era_tag, l.faction_tag,
                   s.slug AS site_slug, s.label AS site_label,
                   src.outlet AS source_outlet, src.title AS source_title,
                   src.url AS source_url, src.kind AS source_kind
            FROM lore l
                 LEFT JOIN site s ON l.site_id = s.id
                 LEFT JOIN source src ON l.source_id = src.id
            WHERE l.spice >= 4 ORDER BY l.spice DESC, l.ord
        """)

    # Source-kind breakdown for the stats bar.
    source_kind_counts = dict(cur.execute(
        'SELECT kind, COUNT(*) FROM source GROUP BY kind ORDER BY 2 DESC'
    ).fetchall())

    persons = []
    if HAS_PERSON:
        persons = fetch_dicts(cur, """
            SELECT p.id, p.slug, p.name, p.name_kana, p.role, p.faction_tag,
                   p.born, p.died, p.body, p.spice,
                   s.slug AS site_slug, s.label AS site_label,
                   src.kind AS source_kind, src.outlet AS source_outlet,
                   src.url AS source_url
            FROM person p
                 LEFT JOIN site s ON p.site_id = s.id
                 LEFT JOIN source src ON p.source_id = src.id
            ORDER BY p.id
        """)

    crime_stats = {}
    if HAS_STAT:
        rows = fetch_dicts(cur, """
            SELECT cs.metric, cs.year, cs.value, cs.unit, cs.notes,
                   src.outlet AS source_outlet, src.kind AS source_kind
            FROM crime_stat cs
                 LEFT JOIN source src ON cs.source_id = src.id
            ORDER BY cs.metric, cs.year
        """)
        for r in rows:
            crime_stats.setdefault(r['metric'], []).append(r)

    org_tree = []
    if HAS_ORGTREE:
        org_tree = fetch_dicts(cur, """
            SELECT child, parent, kind, started, ended, notes, faction_tag
            FROM org_tree
        """)

    total_lore = cur.execute('SELECT COUNT(*) FROM lore').fetchone()[0] if HAS_LORE else 0
    total_sources = cur.execute('SELECT COUNT(*) FROM source').fetchone()[0]
    counts = {
        'sites': len(sites),
        'events': len(timeline),
        'chronicle': len(chronicle),
        'prosecutions': len(prosecutions),
        'testimony': sum(len(s['testimony']) for s in sites),
        'imagery_frames': sum(len(s['imagery']) for s in sites),
        'images': sum(len(s['images']) for s in sites),
        'life': sum(len(s['life']) for s in sites),
        'poi': sum(len(s['poi']) for s in sites),
        'lore': total_lore,
        'persons': len(persons),
        'sources_total': total_sources,
        'crime_stat_points': sum(len(v) for v in crime_stats.values()),
    }

    payload = {
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'sites': sites,
        'chronicle': chronicle,
        'prosecutions': prosecutions,
        'timeline': timeline,
        'floating_lore': floating_lore,
        'counts': counts,
        'palettes': {
            'faction': FACTION_PALETTE,
            'era': ERA_PALETTE,
            'kind': KIND_PALETTE,
            'era_order': ERA_ORDER,
            'faction_order': FACTION_ORDER,
            'source_kind': SOURCE_KIND_BADGE,
        },
        'source_kind_counts': source_kind_counts,
        'persons': persons,
        'crime_stats': crime_stats,
        'org_tree': org_tree,
    }

    html = HTML_TEMPLATE.replace('__PAYLOAD__', json.dumps(payload, ensure_ascii=False))
    with open(OUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'dash5.py wrote {OUT_HTML}')
    for k, v in counts.items():
        print(f'  {k}: {v}')

    con.close()


HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>小倉組織犯罪史タイムマシン — Kokura Underworld Map</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta property="og:title" content="小倉組織犯罪史タイムマシン — Kokura Underworld Map">
<meta property="og:description" content="工藤會を軸に戦後闇市〜頂上作戦・本部解体までの北九州組織犯罪史を、報道・判決・OFAC制裁・書籍・映像参照などを横断する OSINT 可視化(89拠点・182事件・241出典)">
<meta property="og:url" content="https://morigori1.github.io/kokura-underworld-map/">
<meta property="og:type" content="website">
<meta property="og:image" content="https://morigori1.github.io/kokura-underworld-map/images/kudokai_hq_kandake_4.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="小倉組織犯罪史タイムマシン">
<meta name="twitter:description" content="工藤會を軸とする北九州組織犯罪史の OSINT 可視化(89拠点・182事件・241出典・13メディア種別)">
<meta name="twitter:image" content="https://morigori1.github.io/kokura-underworld-map/images/kudokai_hq_kandake_4.jpg">
<link rel="stylesheet" href="vendor/leaflet/leaflet.css">
<script src="vendor/leaflet/leaflet.js"></script>
<style>
  :root {
    --bg: #0a0c10;
    --bg2: #14171c;
    --panel: rgba(20,23,28,0.94);
    --ink: #ecedee;
    --ink-dim: #aab0b8;
    --accent: #d9534f;
    --accent2: #f5b041;
    --accent3: #3498db;
    --gold: #f1c40f;
    --line: #2a2f38;
  }
  html, body { margin:0; padding:0; height:100%; background:var(--bg); color:var(--ink);
               font-family:"Hiragino Sans","Yu Gothic UI",system-ui,sans-serif; overflow:hidden; }
  #map { position:absolute; inset:0; background:var(--bg); }
  a { color:var(--accent3); }

  /* ===== Top bar ===== */
  #topbar {
    position:absolute; top:0; left:0; right:0; height:50px; z-index:1100;
    background:linear-gradient(180deg, rgba(13,15,18,0.97), rgba(13,15,18,0.7));
    border-bottom:1px solid var(--line);
    display:flex; align-items:center; padding:0 16px; gap:18px;
  }
  #topbar .title { font-weight:700; letter-spacing:0.04em; font-size:14px; }
  #topbar .sub   { color:var(--ink-dim); font-size:11px; margin-top:2px; }
  #topbar .stats { margin-left:auto; display:flex; gap:14px; font-size:12px; color:var(--ink-dim); }
  #topbar .stats b { color:var(--accent2); }

  /* ===== Global search bar ===== */
  #search-wrap {
    position:relative; flex-shrink:0;
  }
  #search-input {
    background:rgba(255,255,255,0.06); border:1px solid var(--line);
    color:var(--ink); padding:6px 10px; border-radius:14px;
    font-size:12px; outline:none; min-width:180px;
    transition:border-color 0.2s, min-width 0.25s;
  }
  #search-input:focus { border-color:var(--accent2); min-width:260px; }
  #search-input::placeholder { color:var(--ink-dim); }
  #search-results {
    position:absolute; top:100%; right:0; left:0; margin-top:4px;
    max-height:60vh; overflow-y:auto;
    background:var(--panel); border:1px solid var(--accent2); border-radius:6px;
    padding:6px; z-index:1500;
    display:none;
    box-shadow:0 8px 20px rgba(0,0,0,0.5);
    min-width:320px;
  }
  #search-results.show { display:block; }
  #search-results .group {
    color:var(--accent2); font-size:10px; letter-spacing:0.08em;
    padding:6px 4px 2px; border-top:1px dashed var(--line); margin-top:4px;
  }
  #search-results .group:first-child { border-top:none; margin-top:0; }
  #search-results .hit {
    padding:6px 8px; border-radius:4px; cursor:pointer;
    font-size:12px; color:var(--ink);
    display:flex; align-items:center; gap:8px;
  }
  #search-results .hit:hover { background:rgba(255,255,255,0.06); }
  #search-results .hit .ico { width:18px; flex-shrink:0; text-align:center; }
  #search-results .hit .lbl { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  #search-results .hit .sub { color:var(--ink-dim); font-size:10px; flex-shrink:0; }
  #search-results .empty { color:var(--ink-dim); padding:10px; text-align:center; font-size:11px; }
  @media (max-width: 720px) {
    #search-wrap { flex:1; }
    #search-input { min-width:auto; width:100%; font-size:11px; padding:5px 8px; }
    #search-input:focus { min-width:auto; }
    #search-results { right:0; left:0; min-width:auto; }
    /* On mobile, push search results to fill more of screen */
    #search-results { position:fixed; top:42px; max-height:75vh; }
  }

  /* ===== Color mode bar ===== */
  #modebar {
    position:absolute; top:50px; left:0; right:0; height:36px; z-index:1090;
    background:rgba(13,15,18,0.85); border-bottom:1px solid var(--line);
    display:flex; align-items:center; padding:0 14px; gap:14px; font-size:12px;
    overflow-x:auto; white-space:nowrap;
  }
  #modebar .lbl { color:var(--ink-dim); margin-right:4px; }
  #modebar .chip {
    display:inline-block; padding:3px 10px; border-radius:14px;
    border:1px solid var(--line); cursor:pointer; user-select:none;
    background:rgba(255,255,255,0.03);
  }
  #modebar .chip.active { background:var(--accent); border-color:var(--accent); color:#fff; font-weight:600; }
  #modebar .sep { color:var(--line); margin:0 6px; }

  #source-ribbon {
    position:absolute; top:86px; left:340px; right:0; height:30px; z-index:1085;
    background:rgba(10,12,16,0.85); border-bottom:1px solid var(--line);
    display:flex; align-items:center; padding:0 14px; gap:6px;
    font-size:11px; overflow-x:auto; white-space:nowrap;
  }
  #source-ribbon .lbl { color:var(--ink-dim); margin-right:4px; font-size:10px; }
  #source-ribbon .sb {
    display:inline-flex; align-items:center; padding:2px 8px;
    border-radius:10px; border:1px solid var(--line); cursor:pointer;
    background:rgba(0,0,0,0.3); user-select:none;
  }
  #source-ribbon .sb .cnt { color:var(--accent2); margin-left:4px; font-weight:700; }
  #source-ribbon .sb.active { background:rgba(255,255,255,0.08); }

  /* ===== Side panel (chronicle / floating lore) ===== */
  #side {
    position:absolute; top:116px; left:0; bottom:150px; width:340px; z-index:1000;
    background:var(--panel); border-right:1px solid var(--line); overflow:auto;
    padding:14px 16px;
  }
  #side h2 {
    font-size:12px; margin:18px 0 8px; color:var(--accent2); letter-spacing:0.08em;
    cursor:pointer; user-select:none;
    display:flex; align-items:center; justify-content:space-between;
  }
  #side h2:first-of-type { margin-top:0; }
  #side h2::after { content:'▾'; font-size:11px; color:var(--ink-dim); transition:transform 0.18s; }
  #side h2.collapsed::after { transform:rotate(-90deg); }
  #side h2.collapsed + .section-body { display:none; }
  #side .section-body { overflow:hidden; }

  /* TOC at top of side panel */
  #toc {
    background:rgba(0,0,0,0.35); border:1px solid var(--line);
    border-radius:6px; padding:8px 10px; margin:0 0 14px;
    font-size:11px; line-height:1.8;
  }
  #toc .label { color:var(--ink-dim); font-size:10px; letter-spacing:0.08em; margin-bottom:4px; }
  #toc a {
    color:var(--ink); text-decoration:none; margin-right:10px;
    border-bottom:1px dotted var(--line); cursor:pointer;
  }
  #toc a:hover { color:var(--accent2); border-bottom-color:var(--accent2); }
  .chron {
    border-left:3px solid var(--line); padding:6px 0 6px 12px; margin:8px 0;
    cursor:pointer; transition: border-color 0.2s, background 0.2s;
  }
  .chron:hover { background:rgba(255,255,255,0.04); }
  .chron .yr { font-weight:700; font-size:11px; letter-spacing:0.04em; }
  .chron .tt { font-weight:600; margin:2px 0; font-size:13px; }
  .chron .bd { color:var(--ink-dim); font-size:12px; line-height:1.5; }
  .chron .tags { margin-top:4px; }
  .tag {
    display:inline-block; font-size:10px; padding:1px 6px; border-radius:8px;
    margin-right:4px; background:rgba(255,255,255,0.06); border:1px solid var(--line);
  }
  .src-badge {
    display:inline-block; font-size:10px; padding:1px 6px; border-radius:8px;
    margin-right:4px; background:rgba(0,0,0,0.25); border:1px solid var(--line);
    font-weight:600;
  }
  .person-card {
    border:1px solid var(--line); border-radius:6px; padding:10px;
    margin:8px 0; background:rgba(46,204,113,0.04); font-size:12px; cursor:pointer;
  }
  .person-card:hover { border-color:var(--accent3); }
  .person-card .nm { font-weight:700; color:var(--ink); font-size:14px; }
  .person-card .kana { color:var(--ink-dim); font-size:11px; }
  .person-card .role { font-size:10px; padding:1px 6px; border-radius:8px;
                       border:1px solid var(--line); margin-left:6px;
                       color:var(--accent3); }
  .person-card .lifeyr { color:var(--ink-dim); font-size:11px; margin-top:2px; }
  .person-card .bio { color:var(--ink-dim); line-height:1.5; margin-top:6px;
                      display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
  .stat-card {
    border:1px solid var(--line); border-radius:6px; padding:10px;
    margin:8px 0; background:rgba(0,0,0,0.25);
  }
  .stat-card .tt { font-size:12px; color:var(--accent2); font-weight:600; }
  .stat-card .sub { color:var(--ink-dim); font-size:10px; margin-top:2px; }
  .stat-card svg { display:block; margin-top:8px; }
  .stat-card .axis { font-size:9px; fill:var(--ink-dim); }
  .stat-card .gridline { stroke:var(--line); stroke-width:0.5; }
  .stat-card .line    { stroke:var(--accent); fill:none; stroke-width:1.6; }
  .stat-card .dot     { fill:var(--accent); }
  .stat-card .annot   { font-size:9px; fill:var(--accent2); }
  .org-tree {
    font-size:11px; line-height:1.6;
  }
  .org-tree .node {
    border:1px solid var(--line); border-radius:4px; padding:3px 8px;
    margin:2px 0; background:rgba(0,0,0,0.25); cursor:default;
    display:inline-block;
  }
  .org-tree .node.root { background:rgba(217,83,79,0.1); border-color:var(--accent); }
  .org-tree .lvl { padding-left:14px; border-left:1px dashed var(--line); margin-left:8px; }
  .org-tree .meta { color:var(--ink-dim); font-size:10px; margin-left:6px; }
  .pros { border:1px solid var(--line); border-radius:6px; padding:10px;
          margin:8px 0; background:rgba(0,0,0,0.25); font-size:12px; }
  .pros .dt { color:var(--accent); font-weight:700; }
  .pros .nm { color:var(--ink); font-weight:600; margin-top:2px; }
  .pros .ct { color:var(--ink-dim); }
  .pros .ou { color:var(--accent2); margin-top:4px; font-weight:600; }
  .pros .sm { color:var(--ink-dim); margin-top:4px; line-height:1.4; }

  .lore-card {
    border:1px solid var(--gold); background:linear-gradient(180deg, rgba(241,196,15,0.08), rgba(241,196,15,0.02));
    border-radius:6px; padding:10px; margin:8px 0; font-size:12px; cursor:pointer;
  }
  .lore-card .yr { color:var(--gold); font-weight:700; font-size:11px; }
  .lore-card .tt { color:var(--ink); font-weight:600; margin:2px 0; }
  .lore-card .bd { color:var(--ink-dim); line-height:1.55; }
  .lore-card .stars { color:var(--gold); font-size:11px; margin-top:4px; }

  /* ===== Detail panel ===== */
  #detail {
    position:absolute; top:116px; right:0; bottom:150px; width:440px;
    background:var(--panel); border-left:1px solid var(--line);
    overflow:auto; padding:18px 22px; z-index:1050;
    transform: translateX(100%); transition: transform 0.32s ease;
  }
  #detail.open { transform: translateX(0); }
  #detail .close { float:right; cursor:pointer; color:var(--ink-dim); font-size:18px; padding:2px 8px; }
  #detail .close:hover { color:var(--accent); }
  #detail h2 { margin:0 0 4px; color:var(--accent2); font-size:18px; }
  #detail .meta { color:var(--ink-dim); font-size:12px; margin-bottom:14px; }
  #detail .badges { margin:6px 0 14px; }
  #detail .image { margin:12px 0; }
  #detail .image img { width:100%; border-radius:6px; display:block; }
  #detail .image .cap { font-size:11px; color:var(--ink-dim); margin-top:4px; line-height:1.4; }
  #detail h3 { font-size:11px; color:var(--accent2); margin:18px 0 8px;
               letter-spacing:0.08em; text-transform:uppercase; }
  #detail .narr p { font-size:13px; line-height:1.75; margin:0 0 12px; }
  #detail .narr .nt { font-weight:600; color:var(--ink); margin:8px 0 4px; font-size:13px; }
  #detail .evlist .ev {
    border-left:3px solid var(--accent); padding:6px 10px; margin:8px 0;
    background:rgba(217,83,79,0.06); font-size:12px; border-radius:0 4px 4px 0;
  }
  #detail .evlist .ev .dt { font-weight:700; }
  #detail .evlist .ev .tt { font-weight:600; margin:2px 0; }
  #detail .evlist .ev .sm { color:var(--ink-dim); line-height:1.5; margin-top:4px; }
  #detail .evlist .ev .meta { color:var(--ink-dim); font-size:11px; font-style:italic; }
  #detail .quote {
    border-left:3px solid var(--accent2); padding:6px 12px;
    margin:8px 0; background:rgba(245,176,65,0.05); font-size:12px;
    line-height:1.6;
  }
  #detail .quote .sp { color:var(--accent2); font-weight:600; margin-top:6px; }
  #detail .quote .src { color:var(--ink-dim); font-size:11px; margin-top:2px; }
  #detail .life {
    border:1px solid var(--line); border-radius:6px; padding:10px;
    margin:8px 0; background:rgba(0,0,0,0.25); font-size:12px;
  }
  #detail .life .tp { color:var(--accent3); font-weight:600; }
  #detail .life .tx { color:var(--ink-dim); line-height:1.55; margin-top:4px; }
  #detail .life .src { color:var(--ink-dim); font-size:11px; margin-top:4px; opacity:0.7; }
  #detail .lore-card { margin:8px 0; }
  #detail .wayback-controls { margin:8px 0 4px; }
  #detail .wayback-controls .slider { width:100%; }
  #detail .wayback-controls .lbl { color:var(--accent); font-weight:700; font-size:13px; }
  #detail .wayback-controls .era { color:var(--ink-dim); font-size:11px; line-height:1.4; margin-top:4px; }

  /* ===== Bottom event timeline ===== */
  #timeline {
    position:absolute; left:340px; right:0; bottom:0; height:150px; z-index:1000;
    background:var(--panel); border-top:1px solid var(--line);
    padding:0;
  }
  #era-ribbon {
    display:flex; height:20px; border-bottom:1px solid var(--line);
    font-size:10px; align-items:stretch;
  }
  #era-ribbon .era-cell {
    flex:1; display:flex; align-items:center; justify-content:center;
    color:#fff; font-weight:600; letter-spacing:0.06em;
    border-right:1px solid rgba(0,0,0,0.4); cursor:pointer;
  }
  #era-ribbon .era-cell.dim { opacity:0.45; }
  #timeline-scroll {
    height:130px; overflow-x:auto; overflow-y:hidden; white-space:nowrap;
    padding:10px 14px; box-sizing:border-box;
  }
  .evt {
    display:inline-block; vertical-align:top; width:240px; margin-right:8px;
    border:1px solid var(--line); border-left-width:3px; border-radius:0 6px 6px 0;
    padding:8px 10px;
    background:rgba(0,0,0,0.3); white-space:normal; font-size:12px; cursor:pointer;
    transition: transform 0.15s, border-color 0.15s;
  }
  .evt:hover { transform: translateY(-2px); }
  .evt.sev-5 { box-shadow:0 0 0 2px rgba(217,83,79,0.4); }
  .evt.kind-lore { border-color:var(--gold); background:rgba(241,196,15,0.06); }
  .evt .dt { font-weight:700; font-size:11px; }
  .evt .tt { font-weight:600; margin:3px 0; color:var(--ink); }
  .evt .sm { color:var(--ink-dim); line-height:1.45;
             display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
  .evt .where { color:var(--accent2); font-size:10px; margin-top:4px; }
  .evt .badges { margin-top:4px; }
  .evt.hidden { display:none; }

  /* ===== Marker / popup ===== */
  .leaflet-popup-content-wrapper { background:#14171c; color:var(--ink);
                                   border-radius:6px; border:1px solid var(--line); }
  .leaflet-popup-content { margin:10px 12px; line-height:1.5; }
  .leaflet-popup-tip { background:#14171c; }
  .pop h3 { margin:0 0 6px; font-size:14px; color:var(--accent2); }
  .pop .kind { color:var(--ink-dim); font-size:11px; }
  .pop .notes { font-size:12px; line-height:1.5; margin-top:6px; color:var(--ink-dim); }
  .pop .open {
    display:inline-block; margin-top:8px; background:var(--accent);
    color:#fff; padding:4px 10px; border-radius:3px; font-size:11px;
    cursor:pointer;
  }
  .pin {
    border-radius:50%; border:2px solid #fff;
    box-shadow:0 0 0 1px rgba(0,0,0,0.5), 0 0 6px rgba(0,0,0,0.4);
  }
  .poi-pin { width:6px; height:6px; border-radius:50%; background:#9aa6b2;
             border:1px solid rgba(0,0,0,0.5); }

  /* ===== Splash ===== */
  #splash {
    position:absolute; inset:0; z-index:2000; background:rgba(6,7,9,0.97);
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    text-align:center; padding:20px;
  }
  #splash h1 { font-size:34px; margin:0 0 4px; letter-spacing:0.10em; }
  #splash .tag { color:var(--accent); font-size:13px; letter-spacing:0.14em; margin-bottom:14px; }
  #splash .sub { color:var(--ink-dim); max-width:640px; line-height:1.8; margin-bottom:28px; font-size:13px; }
  #splash .quote {
    color:var(--gold); font-style:italic; font-size:14px; margin:8px 0 22px;
    max-width:600px; line-height:1.7;
  }
  #splash .quote .sm { color:var(--ink-dim); font-style:normal; font-size:11px; margin-top:4px; letter-spacing:0.04em; }
  #splash button {
    background:var(--accent); color:#fff; border:none; padding:12px 30px;
    border-radius:4px; font-size:14px; font-weight:600; cursor:pointer;
    margin:0 6px; letter-spacing:0.06em;
  }
  #splash button.alt { background:transparent; border:1px solid var(--line); color:var(--ink); }
  #splash button.gold { background:transparent; border:1px solid var(--gold); color:var(--gold); }
  #splash .note { margin-top:22px; font-size:11px; color:var(--ink-dim); max-width:620px; line-height:1.7; }
  #splash .ways {
    display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));
    gap:10px; max-width:760px; margin:14px auto 24px;
  }
  #splash .way {
    background:rgba(255,255,255,0.04); border:1px solid var(--line);
    border-radius:6px; padding:10px 12px; cursor:pointer;
    text-align:left; transition:border-color 0.18s, background 0.18s;
  }
  #splash .way:hover { border-color:var(--accent); background:rgba(217,83,79,0.08); }
  #splash .way .num { color:var(--accent2); font-weight:700; font-size:11px; }
  #splash .way .ttl { font-weight:700; font-size:14px; margin:2px 0 4px; color:var(--ink); }
  #splash .way .desc { font-size:11px; color:var(--ink-dim); line-height:1.55; }

  /* ===== Help overlay ===== */
  #help-overlay {
    position:absolute; inset:0; z-index:1900; background:rgba(0,0,0,0.6);
    display:none; pointer-events:auto;
  }
  #help-overlay.show { display:block; }
  #help-overlay .label {
    position:absolute; background:var(--accent); color:#fff;
    padding:6px 10px; border-radius:4px; font-size:11px; font-weight:600;
    box-shadow:0 0 0 1px rgba(0,0,0,0.5);
  }
  #help-overlay .arrow {
    position:absolute; font-size:18px; color:var(--accent2);
  }
  #help-overlay .close-help {
    position:absolute; bottom:30px; left:50%; transform:translateX(-50%);
    background:var(--accent); color:#fff; border:none; padding:10px 28px;
    border-radius:4px; font-size:13px; font-weight:600; cursor:pointer;
  }
  #help-btn {
    position:absolute; top:170px; right:12px; z-index:1100;
    background:var(--accent2); color:#000; border:none;
    width:34px; height:34px; border-radius:50%; font-size:16px; font-weight:700;
    cursor:pointer; box-shadow:0 0 0 2px rgba(0,0,0,0.4);
  }
  #help-btn:hover { background:#fff; }

  /* ===== Layer toggle ===== */
  #layers {
    position:absolute; top:126px; right:12px; z-index:1100;
    background:var(--panel); border:1px solid var(--line); border-radius:6px;
    padding:8px 10px; font-size:12px;
  }
  #layers label { display:block; margin:3px 0; cursor:pointer; }
  #layers input { vertical-align:middle; margin-right:6px; }

  /* ===== Legend ===== */
  #legend {
    position:absolute; bottom:170px; left:354px; z-index:1100;
    background:var(--panel); border:1px solid var(--line); border-radius:6px;
    padding:8px 10px; font-size:11px; max-width:340px;
  }
  #legend .row { display:flex; align-items:center; margin:3px 0; }
  #legend .sw { width:10px; height:10px; border-radius:50%; margin-right:6px; border:1px solid rgba(0,0,0,0.4); }
  #legend .title { font-weight:700; color:var(--accent2); margin-bottom:4px; }

  /* ===== Tour selection modal ===== */
  #tour-menu {
    position:fixed; inset:0; background:rgba(8,9,11,0.95);
    z-index:1850; display:none;
    overflow-y:auto; padding:20px;
  }
  #tour-menu.show { display:block; }
  #tour-menu .wrap { max-width:760px; margin:0 auto; }
  #tour-menu h2 {
    color:var(--accent2); font-size:22px; letter-spacing:0.06em;
    margin:8px 0 6px; text-align:center;
  }
  #tour-menu .sub {
    color:var(--ink-dim); font-size:12px; text-align:center;
    margin-bottom:18px; line-height:1.6;
  }
  #tour-menu .category {
    border:1px solid var(--line); border-radius:8px; padding:14px;
    margin-bottom:14px; background:rgba(255,255,255,0.02);
  }
  #tour-menu .cat-head {
    color:#fff; font-weight:700; font-size:14px;
    margin-bottom:10px; padding-bottom:6px;
    border-bottom:1px solid var(--line);
    display:flex; align-items:center; gap:8px;
  }
  #tour-menu .cat-color {
    width:10px; height:10px; border-radius:50%;
  }
  #tour-menu .tours {
    display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr));
    gap:8px;
  }
  #tour-menu .tour-card {
    background:rgba(255,255,255,0.04); border:1px solid var(--line);
    border-radius:6px; padding:10px 12px; cursor:pointer;
    transition:border-color 0.18s, background 0.18s;
  }
  #tour-menu .tour-card:hover { border-color:var(--accent); background:rgba(217,83,79,0.08); }
  #tour-menu .tour-card .ttl {
    font-weight:700; font-size:13px; color:var(--ink); margin-bottom:3px;
  }
  #tour-menu .tour-card .desc {
    font-size:11px; color:var(--ink-dim); line-height:1.5;
  }
  #tour-menu .tour-card .stops {
    margin-top:6px; font-size:10px; color:var(--accent2);
  }
  #tour-menu .close-menu {
    position:absolute; top:14px; right:18px;
    width:36px; height:36px; border-radius:50%;
    background:var(--accent); color:#fff; border:none;
    font-size:18px; cursor:pointer;
  }

  /* ===== Tour overlay ===== */
  #tour-banner {
    position:absolute; top:120px; left:50%; transform:translateX(-50%); z-index:1080;
    background:rgba(13,15,18,0.88); border:1px solid var(--accent2);
    color:var(--ink); padding:12px 24px; border-radius:6px;
    font-size:14px; font-weight:600; letter-spacing:0.06em;
    box-shadow:0 0 30px rgba(245,176,65,0.3);
    display:none;
  }
  #tour-banner.show { display:block; animation: fadein 0.6s; }
  @keyframes fadein { from { opacity:0; transform:translate(-50%, 10px); } to { opacity:1; transform:translate(-50%, 0); } }

  /* ===== Tour playback controls — always above detail/side panels ===== */
  #tour-controls {
    position:fixed; left:50%; transform:translateX(-50%);
    top:130px;
    background:rgba(13,15,18,0.96); border:1px solid var(--accent2);
    border-radius:30px; padding:6px 8px;
    z-index:1300;
    display:none;
    box-shadow:0 4px 14px rgba(0,0,0,0.7);
  }
  #tour-controls.show { display:flex; align-items:center; gap:4px; }
  #tour-controls button {
    width:36px; height:36px; border-radius:50%;
    border:none; background:transparent; color:var(--ink);
    font-size:14px; cursor:pointer;
    display:flex; align-items:center; justify-content:center;
  }
  #tour-controls button:hover { background:rgba(255,255,255,0.1); }
  #tour-controls .play-pause {
    background:var(--accent); color:#fff; font-size:16px;
  }
  #tour-controls .stop { color:var(--ink-dim); }
  #tour-controls .pos {
    color:var(--ink-dim); font-size:11px; padding:0 8px; font-weight:600;
  }
  #tour-controls .label {
    color:var(--accent2); font-size:11px; font-weight:600;
    padding:0 8px; max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
  }
  @media (max-width: 720px) {
    /* On mobile the timeline is at top (40-150/210px) so we put tour
       controls right above the bottom detail sheet — visible during a
       tour without colliding with the timeline above. */
    #tour-controls {
      top:auto;
      bottom:calc(40vh + 14px);   /* sits 14px above detail sheet (40vh in tour mode) */
      transform:translateX(-50%);
      padding:8px 6px;
    }
    #tour-controls button {
      width:42px; height:42px; font-size:16px;
    }
    #tour-controls .play-pause { font-size:18px; }
    #tour-controls .label { display:none; }
    #tour-controls .pos { font-size:12px; padding:0 6px; }
  }

  @media (max-width: 900px) {
    #side { width:300px; }
    #detail { width:90%; }
    #timeline { left:300px; }
    #legend { left:314px; }
  }

  /* ===== Mobile ===== */
  @media (max-width: 720px) {
    /* Top bar: ultra-compact, only title + key stats */
    #topbar { height:40px; padding:0 10px; gap:6px; }
    #topbar .title { font-size:12px; }
    #topbar .sub { display:none; }
    #topbar .stats { gap:6px; font-size:10px; }
    #topbar .stats span:nth-of-type(n+3) { display:none; }
    #topbar .stats small { display:none; }

    /* Mode bar + source ribbon: HIDDEN on mobile by default — surface via filter modal */
    #modebar, #source-ribbon { display:none; }
    #modebar.show-mobile, #source-ribbon.show-mobile {
      display:flex !important;
      position:relative; top:auto;
    }

    /* Filter modal — opened by 🔍 button */
    #filter-modal {
      position:fixed; top:40px; left:0; right:0; bottom:auto;
      max-height:60vh; overflow-y:auto;
      background:var(--panel); border-bottom:2px solid var(--accent);
      box-shadow:0 6px 20px rgba(0,0,0,0.5);
      padding:14px 16px; z-index:1100;
      transform:translateY(-110%); transition:transform 0.3s ease;
    }
    #filter-modal.show { transform:translateY(0); }
    #filter-modal h3 { font-size:11px; color:var(--accent2); margin:0 0 6px; letter-spacing:0.08em; }
    #filter-modal .group { margin-bottom:14px; }
    #filter-modal .chips { display:flex; flex-wrap:wrap; gap:6px; }
    #filter-modal .chip {
      display:inline-block; padding:4px 10px; border-radius:14px;
      border:1px solid var(--line); cursor:pointer; user-select:none;
      background:rgba(255,255,255,0.03); font-size:11px;
    }
    #filter-modal .chip.active { background:var(--accent); color:#fff; }
    #filter-modal .close-modal {
      display:block; width:100%; margin-top:8px;
      background:var(--accent); color:#fff; border:none;
      padding:10px; border-radius:4px; font-size:13px; font-weight:600;
    }

    /* Side panel becomes a slide-up drawer — fully hidden by default,
       capped at 50vh so the map always gets at least half the screen */
    #side {
      position:fixed; top:auto; left:0; right:0; bottom:0; width:100%;
      max-height:50vh; height:50vh;
      z-index:1060;
      transform:translateY(100%);
      transition:transform 0.3s ease;
      border-right:none; border-top:2px solid var(--accent);
      border-radius:14px 14px 0 0;
      padding:14px 14px 16px;
      box-shadow:0 -6px 20px rgba(0,0,0,0.5);
    }
    #side::before { display:none; }  /* no peek tab; opened via toolbar */
    #detail { z-index:1100; }
    #side.open { transform:translateY(0); }
    #side::before {
      content:'目次 ━━━ タップで展開'; display:block;
      text-align:center; color:var(--accent2); font-size:11px;
      padding:8px 0 6px; letter-spacing:0.08em; font-weight:700;
      border-bottom:1px solid var(--line); margin-bottom:8px; cursor:pointer;
    }
    #side.open::before { content:'━━━ タップで閉じる'; }
    #toc a { display:inline-block; margin:2px 6px 2px 0; }

    /* Detail panel: bottom sheet — capped at <half screen on mobile.
       Default 48vh, tour mode 40vh. Map always gets ≥52vh / 60vh. */
    #detail {
      position:fixed; top:auto; left:0; right:0; bottom:0;
      width:100%; max-width:none;
      height:48vh; max-height:48vh;
      border-left:none; border-top:2px solid var(--accent);
      border-radius:14px 14px 0 0;
      padding:8px 16px 18px;
      transform:translateY(100%);
      transition:transform 0.32s ease, height 0.32s ease;
      box-shadow:0 -6px 20px rgba(0,0,0,0.5);
    }
    #detail.open { transform:translateY(0); }
    /* When a tour is active, shrink further so map gets 60vh */
    body.tour-active #detail { height:40vh; max-height:40vh; }
    /* Drag handle at top */
    #detail::before {
      content:''; display:block;
      width:42px; height:4px; border-radius:2px;
      background:var(--ink-dim); opacity:0.5;
      margin:6px auto 8px;
    }
    /* Larger close button at top-right */
    #detail .close {
      position:absolute; top:6px; right:10px;
      width:36px; height:36px;
      display:flex; align-items:center; justify-content:center;
      background:var(--accent); color:#fff;
      border-radius:50%; font-size:18px; font-weight:700;
      box-shadow:0 2px 6px rgba(0,0,0,0.5);
      float:none; padding:0;
    }
    #detail .close:hover { color:#fff; background:var(--accent); }
    #detail h2 { padding-right:50px; font-size:16px; }
    #detail .image img { max-height:200px; object-fit:cover; }
    #detail h3 { margin:14px 0 6px; }
    #detail .narr p { font-size:12.5px; line-height:1.65; }

    /* Timeline: TOP-mounted on mobile — 4 collapsible states.
       hidden: completely gone (0px) — only re-open tab visible
       min:    era ribbon only (22px)
       cards:  era ribbon + card scroll (110px) — default
       exp:    cards + badges + full summary (170px) */
    #timeline {
      top:40px; bottom:auto; left:0; right:0;
      border-top:none; border-bottom:2px solid var(--accent);
      transition:height 0.25s ease, border-width 0.25s ease;
      z-index:1080;
      height:110px;
      overflow:visible;  /* let the expand-tab stick out below */
    }
    body.timeline-hidden #timeline { height:0; border-bottom-width:0; }
    body.timeline-min    #timeline { height:22px; }
    body.timeline-cards  #timeline { height:110px; }
    body.timeline-exp    #timeline { height:170px; }

    #timeline-scroll { height:88px; padding:6px 8px; transition:height 0.25s ease, padding 0.25s ease; overflow-x:auto; overflow-y:hidden; }
    body.timeline-hidden #timeline-scroll,
    body.timeline-min    #timeline-scroll { height:0; padding:0; overflow:hidden; }
    body.timeline-exp    #timeline-scroll { height:148px; padding:8px 10px; }

    .evt { width:180px; padding:5px 8px; font-size:11px; }
    body.timeline-exp .evt { width:220px; padding:6px 10px; font-size:12px; }
    .evt .sm { -webkit-line-clamp:2; font-size:10.5px; }
    body.timeline-exp .evt .sm { -webkit-line-clamp:3; font-size:11px; }
    .evt .badges { display:none; }
    body.timeline-exp .evt .badges { display:block; }

    #era-ribbon { height:20px; font-size:10px; transition:height 0.25s ease, opacity 0.25s ease; }
    body.timeline-min #era-ribbon { height:18px; font-size:9px; }
    body.timeline-hidden #era-ribbon { height:0; opacity:0; overflow:hidden; }

    /* Toggle tab: simple arrow button — always visible, easy tap target.
       In hidden mode, tab becomes a fixed-position circular button at top. */
    #timeline-expand-tab {
      position:absolute; top:auto; bottom:-30px; right:10px;
      width:44px; height:30px;
      background:var(--accent); color:#fff;
      border:none; border-radius:0 0 8px 8px;
      font-size:18px; font-weight:700; cursor:pointer;
      box-shadow:0 2px 8px rgba(0,0,0,0.5);
      z-index:1500;
      user-select:none; -webkit-tap-highlight-color:rgba(255,255,255,0.3);
      pointer-events:auto;
      display:flex; align-items:center; justify-content:center;
      padding:0;
      transition:background 0.15s, transform 0.15s;
    }
    #timeline-expand-tab:active { transform:scale(0.92); background:#b71c1c; }
    body.timeline-hidden #timeline-expand-tab {
      position:fixed; top:46px; right:10px; bottom:auto;
      width:44px; height:44px;
      border-radius:50%;
      background:var(--accent2); color:#000;
      font-size:20px;
      box-shadow:0 4px 12px rgba(0,0,0,0.6);
      border:2px solid #fff;
    }

    /* Legend hidden on mobile */
    #legend { display:none; }

    /* All floating controls stack on the RIGHT EDGE vertically.
       Heights: help-btn 34px, layers ~42px → 8px gap between them. */
    #layers {
      bottom:auto; right:8px;
      padding:5px 8px; font-size:10px;
      background:var(--panel); border:1px solid var(--line);
      width:auto; max-width:120px;
    }
    #layers label { margin:1px 0; display:block; }
    #help-btn {
      bottom:auto; right:8px;
      width:34px; height:34px; font-size:13px;
    }
    /* Mobile FAB stack — LEFT EDGE, doesn't conflict with right-edge stack */
    #mobile-fab-stack {
      position:fixed; left:8px; bottom:auto; z-index:1110;
      display:flex; flex-direction:column; gap:6px;
    }
    #mobile-fab-stack button {
      width:42px; height:42px; border-radius:50%;
      border:none; font-size:18px; font-weight:700; cursor:pointer;
      box-shadow:0 2px 8px rgba(0,0,0,0.5);
      display:flex; align-items:center; justify-content:center;
    }
    #fab-filter { background:var(--accent2); color:#000; }
    #fab-menu { background:var(--accent3); color:#fff; }
    /* On mobile, the right-side floating help/layers are HIDDEN —
       their functions are consolidated into the left FAB stack. */
    #help-btn, #layers { display:none !important; }

    /* FAB stack on LEFT edge — 6 buttons, smaller on mobile */
    #mobile-fab-stack button {
      width:38px; height:38px; font-size:16px;
    }
    body.timeline-hidden #mobile-fab-stack { top:94px;  }
    body.timeline-min    #mobile-fab-stack { top:96px;  }
    body.timeline-cards  #mobile-fab-stack { top:184px; }
    body.timeline-exp    #mobile-fab-stack { top:244px; }
    #mobile-fab-stack { transition:top 0.25s ease; }

    /* Splash: smaller, single-column */
    #splash { padding:14px; overflow-y:auto; align-items:flex-start; padding-top:30px; }
    #splash h1 { font-size:22px; }
    #splash .tag { font-size:11px; }
    #splash .sub { font-size:12px; }
    #splash .quote { font-size:13px; margin:6px 0 16px; }
    #splash .ways { grid-template-columns:1fr; max-width:none; gap:8px; margin:6px 0 16px; }
    #splash .way { padding:8px 10px; }
    #splash button { padding:10px 22px; font-size:13px; margin:4px 4px 0; display:inline-block; }
    #splash .note { font-size:10px; }

    /* Marker pins easier to tap */
    .pin { box-shadow:0 0 0 1px rgba(0,0,0,0.6), 0 0 4px rgba(0,0,0,0.6); }

    /* Stat chart full width */
    .stat-card svg { width:100% !important; height:auto; }

  }
  @media (min-width: 721px) {
    #mobile-fab-stack { display:none !important; }
    #filter-modal { display:none !important; }
    #timeline-expand-tab { display:none !important; }
  }
  #mobile-toggle { display:none !important; }
</style>
</head>
<body>

<div id="splash">
  <div class="tag">KOKURA UNDERWORLD MAP</div>
  <h1>小倉組織犯罪史タイムマシン</h1>
  <div class="sub">
    工藤會を軸に戦後闇市〜頂上作戦・本部解体までを、報道・判決・OFAC制裁・<br>
    書籍・映像参照を横断する OSINT で 1 枚の地図に。
    <br>
    <span style="color:var(--accent2); font-size:11px;">
      89 拠点 · 182 事件 · 102 軼話 · 241 出典 / 13 メディア種別
    </span>
  </div>
  <div class="quote">
    「生涯後悔するぞ」<br>
    <span class="sm">— 2021-08-24 一審 死刑判決言渡時の在廷発言と報じられた言葉</span>
  </div>

  <div class="ways">
    <div class="way" data-way="hq">
      <div class="num">▶ 1</div>
      <div class="ttl">本部跡から始める</div>
      <div class="desc">神岳1丁目に立っていた「金看板」と 2019年解体までの軌跡。最も濃いストーリー。</div>
    </div>
    <div class="way" data-way="tour-chron">
      <div class="num">▶ 2</div>
      <div class="ttl">系譜順に5幕で巡る</div>
      <div class="desc">戦後闇市 → 高度成長 → 平成抗争 → 頂上作戦 → 解体後 の章バナー演出付き。</div>
    </div>
    <div class="way" data-way="tour-gossip">
      <div class="num">▶ 3</div>
      <div class="ttl">ゴシップ層を巡る</div>
      <div class="desc">金看板撤去・草野闇市出自・道仁会抗争・最高裁上告 — 報道書籍の軼話だけで巡回。</div>
    </div>
    <div class="way" data-way="cases-4">
      <div class="num">▶ 4</div>
      <div class="ttl">市民襲撃4事件</div>
      <div class="desc">1998漁協・2012元警官・2013看護師・2014歯科医師 — 頂上作戦の起訴対象。</div>
    </div>
    <div class="way" data-way="tour-menu" style="border-color:#e74c3c;">
      <div class="num" style="color:#e74c3c;">🎬 5</div>
      <div class="ttl">ツアー選択メニュー</div>
      <div class="desc">16 種のガイドツアーを系統別(工藤會・九州抗争・山口組・半グレ・全国比較・カルチャー)から選ぶ。</div>
    </div>
    <div class="way" data-way="map-free">
      <div class="num">▶ 6</div>
      <div class="ttl">自由に地図を開く</div>
      <div class="desc">171 拠点ピンを自由探索。色分け切替・時代/派閥/出典フィルタで読み方を変える。</div>
    </div>
  </div>

  <div class="note">
    エンタメ寄りに振った OSINT 表示です。<br>
    判決・公的記録は青系、報道書籍の軼話(ゴシップ層)は金縁、海外メディアは緑系で色分け。<br>
    被害者の番地・氏名は載せていません。座標は町丁目重心(公的建物は具体的座標)。
  </div>
</div>

<div id="topbar">
  <div>
    <div class="title">小倉組織犯罪史タイムマシン</div>
    <div class="sub">Kokura Underworld Map · OSINT + 軼話レイヤー</div>
  </div>
  <div id="search-wrap">
    <input id="search-input" type="search" placeholder="🔍 拠点・事件・人物・ツアーを検索" autocomplete="off">
    <div id="search-results"></div>
  </div>
  <div class="stats">
    <span>拠点 <b id="stat-sites">0</b></span>
    <span>事件 <b id="stat-events">0</b></span>
    <span>軼話 <b id="stat-lore">0</b></span>
    <span>人物 <b id="stat-persons">0</b></span>
    <span>系譜 <b id="stat-chron">0</b></span>
    <span>出典 <b id="stat-src">0</b><small style="color:var(--ink-dim);">種類</small> / <b id="stat-src-total">0</b></span>
  </div>
</div>

<div id="modebar">
  <span class="lbl">色分け:</span>
  <span class="chip mode active" data-mode="kind">種別</span>
  <span class="chip mode" data-mode="faction">派閥</span>
  <span class="chip mode" data-mode="era">時代</span>
  <span class="sep">│</span>
  <span class="lbl">派閥フィルタ:</span>
  <span id="faction-chips"></span>
</div>

<div id="source-ribbon">
  <span class="lbl">出典:</span>
  <span id="source-chips"></span>
</div>

<div id="side">
  <div id="toc">
    <div class="label">目次 — 各セクションへ</div>
    <a data-jump="sec-chron">系譜</a><a data-jump="sec-tree">系統樹</a><a data-jump="sec-persons">人物</a><a data-jump="sec-pros">訴訟</a><a data-jump="sec-lore">ゴシップ</a><a data-jump="sec-charts">推移</a>
  </div>
  <h2 data-section="sec-chron">組織系譜</h2>
  <div class="section-body" id="sec-chron"><div id="chron-list"></div></div>
  <h2 data-section="sec-tree">組織系統樹</h2>
  <div class="section-body" id="sec-tree"><div id="org-tree" class="org-tree"></div></div>
  <h2 data-section="sec-persons">主要人物(公開人物のみ)</h2>
  <div class="section-body" id="sec-persons"><div id="person-list"></div></div>
  <h2 data-section="sec-pros" class="collapsed">主要訴訟</h2>
  <div class="section-body" id="sec-pros"><div id="pros-list"></div></div>
  <h2 data-section="sec-lore">ゴシップ層(派閥横断)</h2>
  <div class="section-body" id="sec-lore"><div id="lore-list"></div></div>
  <h2 data-section="sec-charts" class="collapsed">推移チャート(警察白書ベース)</h2>
  <div class="section-body" id="sec-charts"><div id="stat-charts"></div></div>
</div>

<div id="layers">
  <label><input type="checkbox" id="toggle-poi"> 周辺 POI</label>
  <label><input type="checkbox" id="toggle-sat"> 衛星(現在)</label>
</div>

<button id="help-btn" title="使い方ガイド">?</button>
<button id="mobile-toggle" title="目次・系譜を開く">☰</button>

<div id="mobile-fab-stack">
  <button id="fab-tour"   type="button" onclick="fabTour()"   title="ツアー選択"     style="background:#e74c3c; color:#fff;">🎬</button>
  <button id="fab-filter" type="button" onclick="fabFilter()" title="絞り込み・色分け" style="background:#f5b041; color:#000;">🔍</button>
  <button id="fab-menu"   type="button" onclick="fabMenu()"   title="目次・系譜・人物" style="background:#3498db; color:#fff;">☰</button>
  <button id="fab-help"   type="button" onclick="fabHelp()"   title="使い方ガイド"   style="background:#f1c40f; color:#000;">?</button>
  <button id="fab-poi"    type="button" onclick="fabPoi()"    title="周辺POIを表示"  style="background:#9aa6b2; color:#fff;">📍</button>
  <button id="fab-sat"    type="button" onclick="fabSat()"    title="衛星画像に切替" style="background:#34495e; color:#fff;">🛰</button>
</div>

<div id="filter-modal">
  <h3>色分けモード</h3>
  <div class="group">
    <div class="chips" id="m-modes">
      <span class="chip active" data-mode="kind">種別</span>
      <span class="chip" data-mode="faction">派閥</span>
      <span class="chip" data-mode="era">時代</span>
    </div>
  </div>
  <h3>派閥フィルタ(複数選択)</h3>
  <div class="group"><div class="chips" id="m-factions"></div></div>
  <h3>出典フィルタ</h3>
  <div class="group"><div class="chips" id="m-sources"></div></div>
  <h3>時代フィルタ</h3>
  <div class="group"><div class="chips" id="m-eras"></div></div>
  <button class="close-modal" id="close-filter">適用して閉じる</button>
</div>

<div id="help-overlay">
  <div class="label" style="top:60px; left:50%; transform:translateX(-50%); max-width:80%; text-align:center;">
    ▲ 上部チップ: 色分けモード切替(種別/派閥/時代)+ 派閥フィルタ + 出典種別フィルタ
  </div>
  <div class="label" style="top:130px; left:16px; max-width:280px;">
    ◀ 左サイド: 系譜・系統樹・人物・訴訟・ゴシップ・推移チャート(目次から飛べる)
  </div>
  <div class="label" style="bottom:170px; left:50%; transform:translateX(-50%); max-width:80%; text-align:center;">
    ▼ 下部: 全182事件タイムライン(時代リボンで絞込・カードクリックで詳細へ)
  </div>
  <div class="label" style="top:180px; right:60px; max-width:240px;">
    ▶ 右上ボタン: POI・衛星トグル・このヘルプ
  </div>
  <div class="label" style="top:260px; left:50%; transform:translateX(-50%); max-width:80%; text-align:center; background:var(--gold); color:#000;">
    ピンをタップ → 「詳細を開く」で右パネルに展開
    <br>(衛星タイムマシン・写真・判決抜粋・軼話・街のいま)
  </div>
  <button class="close-help" id="close-help">わかった</button>
</div>

<div id="legend"></div>
<div id="tour-menu">
  <button class="close-menu" id="close-tour-menu">✕</button>
  <div class="wrap">
    <h2>🎬 ガイドツアーを選ぶ</h2>
    <div class="sub">
      組織系統別に整理した 16 種のツアー。各カード をタップで再生開始。<br>
      再生中は ⏮ / ⏸ / ⏭ で前後・一時停止できます。
    </div>
    <div id="tour-categories"></div>
  </div>
</div>

<div id="tour-banner"></div>

<div id="tour-controls">
  <button class="prev" title="前へ">⏮</button>
  <button class="play-pause" title="一時停止">⏸</button>
  <button class="next" title="次へ">⏭</button>
  <span class="pos" id="tour-pos">1 / 1</span>
  <span class="label" id="tour-label"></span>
  <button class="stop" title="ツアー終了">✕</button>
</div>

<div id="map"></div>

<div id="timeline">
  <button id="timeline-expand-tab" type="button" onclick="cycleTimelineState()" aria-label="タイムライン表示切替">▼</button>
  <div id="era-ribbon"></div>
  <div id="timeline-scroll">
    <div class="empty" id="tl-empty" style="color:var(--ink-dim); font-size:12px; padding:30px 0; text-align:center; white-space:normal;">
      事件タイムラインは phase6_events を実行すると拡充されます。
    </div>
  </div>
</div>

<div id="detail">
  <span class="close" onclick="closeDetail()">✕</span>
  <div id="detail-body"></div>
</div>

<script>
const DATA = __PAYLOAD__;
const FACTION = DATA.palettes.faction;
const ERA = DATA.palettes.era;
const KIND = DATA.palettes.kind;
const ERA_ORDER = DATA.palettes.era_order;
const FACTION_ORDER = DATA.palettes.faction_order;
const SRC_BADGE = DATA.palettes.source_kind;  // {kind: [emoji, label, color]}

function srcBadgeHtml(srcKind) {
  if (!srcKind || !SRC_BADGE[srcKind]) return '';
  const [emoji, label, color] = SRC_BADGE[srcKind];
  return `<span class="src-badge" style="border-color:${color}; color:${color};" title="出典種別: ${label}">${emoji} ${label}</span>`;
}

const SITE_KIND_LABEL = {
  hq_former: '本部跡',
  hq_current: '本部',
  attack_site: '事件発生地',
  district: '街区',
  landmark: 'ランドマーク',
  front: 'フロント',
  lore_site: '軼話地点',
};

let colorMode = 'kind';   // 'kind' | 'faction' | 'era'
const factionFilter = new Set(); // empty = no filter

const map = L.map('map', { zoomControl: true, preferCanvas: true })
  .setView([33.886, 130.880], 14);

const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap',
  maxZoom: 19,
}).addTo(map);

const esriLayer = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  { attribution: '© Esri World Imagery', maxZoom: 19 }
);

let waybackLayer = null;

function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function escapeAttr(s) { return escapeHtml(s).replace(/'/g, ''); }

function colorFor(thing, fallbackKind) {
  if (colorMode === 'faction' && thing.faction_tag && FACTION[thing.faction_tag])
    return FACTION[thing.faction_tag];
  if (colorMode === 'era' && thing.era_tag && ERA[thing.era_tag])
    return ERA[thing.era_tag];
  // kind fallback
  const k = thing.kind || fallbackKind;
  return KIND[k] || '#9aa6b2';
}

function pinSize(severity) {
  if (severity >= 5) return 18;
  if (severity >= 4) return 16;
  if (severity >= 3) return 14;
  if (severity >= 2) return 12;
  return 11;
}

// ===== Plot site markers =====
const siteIndex = {};
function makeMarker(s) {
  const maxSev = (s.events || []).reduce((a,e) => Math.max(a, e.severity || 1), 1);
  const size = pinSize(maxSev);
  const color = colorFor(s);
  const html = `<div class="pin" style="width:${size}px; height:${size}px; background:${color};"></div>`;
  const icon = L.divIcon({ className: '', html, iconSize: [size, size] });
  return L.marker([s.lat, s.lon], { icon, title: s.label });
}

for (const s of DATA.sites) {
  if (s.lat == null || s.lon == null) continue;
  const m = makeMarker(s);
  m.addTo(map);
  m.bindPopup(renderSitePopup(s), { maxWidth: 360 });
  siteIndex[s.slug] = { site: s, marker: m, poiMarkers: [] };
}

function refreshMarkers() {
  for (const slug in siteIndex) {
    const rec = siteIndex[slug];
    map.removeLayer(rec.marker);
    if (factionFilter.size > 0 && rec.site.faction_tag && !factionFilter.has(rec.site.faction_tag)) {
      continue;
    }
    rec.marker = makeMarker(rec.site);
    rec.marker.addTo(map);
    rec.marker.bindPopup(renderSitePopup(rec.site), { maxWidth: 360 });
  }
}

function renderSitePopup(s) {
  const lines = [];
  lines.push(`<div class="pop">`);
  lines.push(`  <h3>${escapeHtml(s.label)}</h3>`);
  const parts = [];
  if (SITE_KIND_LABEL[s.kind]) parts.push(SITE_KIND_LABEL[s.kind]);
  if (s.place) parts.push(escapeHtml(s.place));
  if (s.status) parts.push(escapeHtml(s.status));
  lines.push(`  <div class="kind">${parts.join(' · ')}</div>`);
  if (s.faction_tag || s.era_tag) {
    let badges = '';
    if (s.faction_tag) badges += `<span class="tag" style="border-color:${FACTION[s.faction_tag]||'var(--line)'}; color:${FACTION[s.faction_tag]||'inherit'};">${escapeHtml(s.faction_tag)}</span>`;
    if (s.era_tag)     badges += `<span class="tag" style="border-color:${ERA[s.era_tag]||'var(--line)'}; color:${ERA[s.era_tag]||'inherit'};">${escapeHtml(s.era_tag)}</span>`;
    lines.push(`  <div style="margin:6px 0;">${badges}</div>`);
  }
  if (s.notes) lines.push(`  <div class="notes">${escapeHtml(s.notes.slice(0, 160))}…</div>`);
  lines.push(`  <span class="open" onclick="openDetail('${escapeAttr(s.slug)}')">詳細を開く →</span>`);
  lines.push(`</div>`);
  return lines.join('\n');
}

// ===== Detail panel =====
const detailEl = document.getElementById('detail');
const detailBody = document.getElementById('detail-body');

function badgeHtml(s) {
  let h = '';
  if (s.faction_tag) h += `<span class="tag" style="border-color:${FACTION[s.faction_tag]||'var(--line)'}; color:${FACTION[s.faction_tag]||'inherit'};">${escapeHtml(s.faction_tag)}</span>`;
  if (s.era_tag)     h += `<span class="tag" style="border-color:${ERA[s.era_tag]||'var(--line)'}; color:${ERA[s.era_tag]||'inherit'};">${escapeHtml(s.era_tag)}</span>`;
  return h;
}

function openDetail(slug) {
  const rec = siteIndex[slug];
  if (!rec) return;
  const s = rec.site;
  const html = [];
  html.push(`<h2>${escapeHtml(s.label)}</h2>`);
  const parts = [];
  if (SITE_KIND_LABEL[s.kind]) parts.push(SITE_KIND_LABEL[s.kind]);
  if (s.place) parts.push(escapeHtml(s.place));
  if (s.status) parts.push(escapeHtml(s.status));
  html.push(`<div class="meta">${parts.join(' · ')}</div>`);
  html.push(`<div class="badges">${badgeHtml(s)}</div>`);

  if (s.images && s.images.length) {
    for (const im of s.images) {
      html.push(`<div class="image">`);
      html.push(`  <img src="${escapeAttr(im.path)}" alt="${escapeAttr(im.caption || '')}">`);
      html.push(`  <div class="cap">${escapeHtml(im.caption || '')} <br>` +
                `<small>${escapeHtml(im.credit || '')}` +
                (im.src ? ` · <a href="${escapeAttr(im.src)}" target="_blank" rel="noopener">Commons</a>` : '') +
                `</small></div>`);
      html.push(`</div>`);
    }
  }

  if (s.notes) {
    html.push(`<div class="narr"><p>${escapeHtml(s.notes)}</p></div>`);
  }

  if (s.imagery && s.imagery.length) {
    html.push(`<h3>衛星タイムマシン</h3>`);
    html.push(`<div class="wayback-controls">`);
    html.push(`  <div class="lbl"><span id="wb-date">${escapeHtml(s.imagery[0].date)}</span>` +
              ` <span style="color:var(--ink-dim); font-size:11px;">` +
              `(${s.imagery.length} 異なるフレーム)</span></div>`);
    html.push(`  <input class="slider" type="range" min="0" max="${s.imagery.length - 1}" value="0" id="wb-slider">`);
    html.push(`  <div class="era" id="wb-era"></div>`);
    html.push(`</div>`);
  }

  if (s.narration && s.narration.length) {
    html.push(`<h3>解説</h3><div class="narr">`);
    for (const n of s.narration) {
      html.push(`<div class="nt">${escapeHtml(n.title || '')}</div>`);
      html.push(`<p>${escapeHtml(n.body || '')}</p>`);
    }
    html.push(`</div>`);
  }

  if (s.events && s.events.length) {
    html.push(`<h3>事件・関連イベント</h3><div class="evlist">`);
    for (const e of s.events) {
      const c = colorFor(e);
      html.push(`<div class="ev" style="border-left-color:${c};">`);
      html.push(`  <div class="dt" style="color:${c};">${escapeHtml(e.date || '')}` +
                (e.severity ? ` <span style="color:var(--gold); font-size:10px;">★${e.severity}</span>` : '') + `</div>`);
      html.push(`  <div class="tt">${escapeHtml(e.title || e.kind || '')}</div>`);
      const meta = [];
      if (e.victim_role) meta.push(`被害: ${escapeHtml(e.victim_role)}`);
      if (e.weapon) meta.push(`手段: ${escapeHtml(e.weapon)}`);
      if (e.resolution) meta.push(`結果: ${escapeHtml(e.resolution)}`);
      if (meta.length) html.push(`<div class="meta">${meta.join(' · ')}</div>`);
      if (e.summary) html.push(`<div class="sm">${escapeHtml(e.summary)}</div>`);
      html.push(`<div style="margin-top:6px;">${badgeHtml(e)}${srcBadgeHtml(e.source_kind)}</div>`);
      if (e.outlet || e.url) {
        const link = e.url ? `<a href="${escapeAttr(e.url)}" target="_blank" rel="noopener">${escapeHtml(e.outlet || '出典')} →</a>` : escapeHtml(e.outlet || '');
        html.push(`<div class="sm" style="margin-top:4px;">${link}</div>`);
      }
      html.push(`</div>`);
    }
    html.push(`</div>`);
  }

  if (s.lore && s.lore.length) {
    html.push(`<h3>軼話 / ゴシップ層</h3>`);
    for (const l of s.lore) {
      const stars = '★'.repeat(l.spice || 1);
      html.push(`<div class="lore-card">`);
      html.push(`  <div class="yr">${escapeHtml(l.year || '')}</div>`);
      html.push(`  <div class="tt">${escapeHtml(l.title || '')}</div>`);
      html.push(`  <div class="bd">${escapeHtml(l.body || '')}</div>`);
      html.push(`  <div class="stars">${stars}</div>`);
      html.push(`  <div style="margin-top:6px;">${badgeHtml(l)}${srcBadgeHtml(l.source_kind)}</div>`);
      if (l.source_outlet) {
        const link = l.source_url ? `<a href="${escapeAttr(l.source_url)}" target="_blank" rel="noopener">${escapeHtml(l.source_outlet)} →</a>` : escapeHtml(l.source_outlet);
        html.push(`<div style="font-size:11px; color:var(--ink-dim); margin-top:4px;">出典: ${link}` +
                  (l.source_title ? ` <em>— ${escapeHtml(l.source_title)}</em>` : '') + `</div>`);
      }
      html.push(`</div>`);
    }
  }

  if (s.testimony && s.testimony.length) {
    html.push(`<h3>判決抜粋 / 証言</h3>`);
    for (const t of s.testimony) {
      html.push(`<div class="quote">`);
      html.push(`  ${escapeHtml(t.quote || '')}`);
      html.push(`  <div class="sp">— ${escapeHtml(t.speaker_label || t.role || '')}` +
                (t.year ? ` (${escapeHtml(t.year)})` : '') + `</div>`);
      if (t.source_outlet) {
        html.push(`<div class="src">出典: ${escapeHtml(t.source_outlet)}` +
                  (t.source_title ? ` — ${escapeHtml(t.source_title)}` : '') + `</div>`);
      }
      html.push(`</div>`);
    }
  }

  if (s.life && s.life.length) {
    html.push(`<h3>街のいま</h3>`);
    for (const l of s.life) {
      html.push(`<div class="life">`);
      html.push(`  <div class="tp">${escapeHtml(l.topic || '')}</div>`);
      html.push(`  <div class="tx">${escapeHtml(l.text || '')}</div>`);
      if (l.source_label) html.push(`<div class="src">出典: ${escapeHtml(l.source_label)}</div>`);
      html.push(`</div>`);
    }
  }

  detailBody.innerHTML = html.join('\n');
  detailEl.classList.add('open');

  const slider = document.getElementById('wb-slider');
  if (slider && s.imagery.length) {
    const dateEl = document.getElementById('wb-date');
    const eraEl = document.getElementById('wb-era');
    const eraByYear = {};
    for (const e of (s.eras || [])) eraByYear[String(e.year)] = e.caption;
    function applyFrame(idx) {
      const f = s.imagery[idx];
      dateEl.textContent = f.date;
      const year = (f.date || '').slice(0, 4);
      eraEl.textContent = eraByYear[year] || '';
      if (waybackLayer) { map.removeLayer(waybackLayer); waybackLayer = null; }
      waybackLayer = L.tileLayer(f.url, { maxZoom: 19, opacity: 0.95 }).addTo(map);
      if (s.lat && s.lon) map.setView([s.lat, s.lon], Math.max(map.getZoom(), 17));
    }
    slider.oninput = (e) => applyFrame(parseInt(e.target.value));
    applyFrame(0);
  }

  // Close side panel if it's open (mobile, otherwise no-op)
  document.getElementById('side').classList.remove('open');

  if (s.lat && s.lon) {
    const isMobile = window.matchMedia('(max-width: 720px)').matches;
    if (isMobile) {
      // Detail covers bottom of viewport: 48vh normal, 40vh during tour.
      // (Capped at <half so the map always wins.) Shift map so the marker
      // centers in the visible map band.
      const tourMode = document.body.classList.contains('tour-active');
      const detailVh = tourMode ? 0.40 : 0.48;
      const visibleMapVh = 1 - detailVh;
      const markerCenterVh = visibleMapVh / 2;  // center marker in visible map band
      const targetZoom = Math.max(map.getZoom(), tourMode ? 15 : 16);
      const targetPoint = map.project([s.lat, s.lon], targetZoom);
      const vh = window.innerHeight;
      const shiftY = (0.5 - markerCenterVh) * vh;
      const adjusted = L.point(targetPoint.x, targetPoint.y + shiftY);
      const newCenter = map.unproject(adjusted, targetZoom);
      map.setView(newCenter, targetZoom, { animate: true });
    } else {
      map.setView([s.lat, s.lon], Math.max(map.getZoom(), 16), { animate: true });
    }
  }
}

function closeDetail() {
  detailEl.classList.remove('open');
  if (waybackLayer) { map.removeLayer(waybackLayer); waybackLayer = null; }
}
// Tap on empty map (outside markers) closes the panels on mobile
map.on('click', () => {
  if (!window.matchMedia('(max-width: 720px)').matches) return;
  detailEl.classList.remove('open');
  document.getElementById('side').classList.remove('open');
});
window.openDetail = openDetail;
window.closeDetail = closeDetail;

// ===== Side panel: chronicle =====
const chronEl = document.getElementById('chron-list');
DATA.chronicle.forEach((c, i) => {
  const col = ERA[c.era_tag] || 'var(--line)';
  const d = document.createElement('div');
  d.className = 'chron';
  d.style.borderLeftColor = col;
  d.innerHTML =
    `<div class="yr" style="color:${col};">${escapeHtml(c.year || '')}</div>` +
    `<div class="tt">${escapeHtml(c.title || '')}</div>` +
    `<div class="bd">${escapeHtml((c.body || '').slice(0, 110))}…</div>` +
    `<div class="tags">${badgeHtml(c)}</div>`;
  d.title = c.body || '';
  d.onclick = () => {
    // best-effort: jump to a matched site
    const target = matchChronToSite(c);
    if (target) openDetail(target);
  };
  chronEl.appendChild(d);
});

function matchChronToSite(c) {
  // crude match by year prefix
  const y = (c.year || '').slice(0, 4);
  for (const s of DATA.sites) {
    const fs = (s.first_seen || '').slice(0, 4);
    if (fs && fs === y) return s.slug;
  }
  // map by faction
  if (c.faction_tag === '工藤會' || c.faction_tag === '司法側') return 'kudokai_hq_kandake';
  if (c.faction_tag === '草野一家系') return 'kusano_ikka_origin_kokura';
  if (c.faction_tag === '工藤組系') return 'kudogumi_nakatsu_origin';
  if (c.faction_tag === '山口組系') return 'yamaguchigumi_kyushu_entry';
  if (c.faction_tag === '道仁会系') return 'kurume_dojinkai_hq';
  if (c.faction_tag === '田中組系') return 'tanaka_gumi_offshoot';
  if (c.faction_tag === '県警側') return 'fukuoka_kenkei';
  return 'kudokai_hq_kandake';
}

// ===== Side panel: prosecutions =====
const prosEl = document.getElementById('pros-list');
for (const p of DATA.prosecutions) {
  const d = document.createElement('div');
  d.className = 'pros';
  d.innerHTML =
    `<div class="dt">${escapeHtml(p.decided_on || '')} · ${escapeHtml(p.court || '')} ${escapeHtml(p.stage || '')}</div>` +
    `<div class="nm">${escapeHtml(p.defendant_label || '')}</div>` +
    `<div class="ct">${escapeHtml(p.case_label || '')}</div>` +
    `<div class="ou">${escapeHtml(p.outcome || '')}</div>` +
    (p.summary ? `<div class="sm">${escapeHtml(p.summary)}</div>` : '');
  prosEl.appendChild(d);
}

// ===== Side panel: persons =====
const personEl = document.getElementById('person-list');
for (const p of (DATA.persons || [])) {
  const d = document.createElement('div');
  d.className = 'person-card';
  const lifeyr = (p.born || p.died) ? `${p.born || ''} – ${p.died || ''}` : '';
  d.innerHTML =
    `<div><span class="nm">${escapeHtml(p.name || '')}</span>` +
    (p.kana ? ` <span class="kana">${escapeHtml(p.name_kana || '')}</span>` : '') +
    (p.role ? ` <span class="role" style="color:${FACTION[p.faction_tag]||'var(--accent3)'};">${escapeHtml(p.role)}</span>` : '') +
    `</div>` +
    (lifeyr ? `<div class="lifeyr">${escapeHtml(lifeyr)}</div>` : '') +
    `<div class="bio">${escapeHtml(p.body || '')}</div>` +
    `<div style="margin-top:6px;">${badgeHtml(p)}${srcBadgeHtml(p.source_kind)}</div>`;
  if (p.site_slug) d.onclick = () => openDetail(p.site_slug);
  personEl.appendChild(d);
}

// ===== Side panel: org tree =====
const orgTreeEl = document.getElementById('org-tree');
const tree = DATA.org_tree || [];
// Build adjacency: parent -> [children]. Roots have parent === null.
const childMap = new Map();
const allNodes = new Set();
const treeRows = new Map();
for (const e of tree) {
  if (!childMap.has(e.parent || '')) childMap.set(e.parent || '', []);
  childMap.get(e.parent || '').push(e);
  allNodes.add(e.child);
  if (e.parent) allNodes.add(e.parent);
  treeRows.set(e.child, e);
}
const rendered = new Set();
function renderOrgNode(name, depth) {
  if (rendered.has(name)) return;
  rendered.add(name);
  const row = treeRows.get(name);
  const wrap = document.createElement('div');
  wrap.className = depth === 0 ? '' : 'lvl';
  wrap.style.marginLeft = (depth * 4) + 'px';
  const node = document.createElement('div');
  node.className = 'node' + (depth === 0 ? ' root' : '');
  const col = row && FACTION[row.faction_tag] ? FACTION[row.faction_tag] : 'var(--accent3)';
  node.style.borderColor = col;
  node.style.color = col;
  let meta = '';
  if (row) {
    const yr = [row.started, row.ended].filter(Boolean).join('–');
    meta = `<span class="meta">${escapeHtml(yr)}</span>`;
  }
  node.innerHTML = `${escapeHtml(name)}${meta}`;
  wrap.appendChild(node);
  orgTreeEl.appendChild(wrap);
  // recurse children
  const children = childMap.get(name) || [];
  for (const c of children) {
    if (rendered.has(c.child)) continue;
    const subWrap = document.createElement('div');
    subWrap.style.marginLeft = ((depth + 1) * 4) + 'px';
    orgTreeEl.appendChild(subWrap);
    // delegate via DOM insertion
    renderOrgNode(c.child, depth + 1);
  }
}
const roots = (childMap.get('') || []);
for (const r of roots) renderOrgNode(r.child, 0);
// any remaining unrendered (cycles / orphans): render at depth 0
for (const name of allNodes) {
  if (!rendered.has(name)) renderOrgNode(name, 0);
}

// ===== Side panel: top-spice lore drawer =====
const loreEl = document.getElementById('lore-list');
for (const l of DATA.floating_lore) {
  const d = document.createElement('div');
  d.className = 'lore-card';
  const stars = '★'.repeat(l.spice || 1);
  d.innerHTML =
    `<div class="yr">${escapeHtml(l.year || '')}</div>` +
    `<div class="tt">${escapeHtml(l.title || '')}</div>` +
    `<div class="bd">${escapeHtml((l.body || '').slice(0, 160))}…</div>` +
    `<div class="stars">${stars}</div>` +
    `<div style="margin-top:4px;">${srcBadgeHtml(l.source_kind)}</div>` +
    (l.site_label ? `<div style="font-size:10px; color:var(--ink-dim); margin-top:4px;">@ ${escapeHtml(l.site_label)}</div>` : '');
  if (l.site_slug) d.onclick = () => openDetail(l.site_slug);
  loreEl.appendChild(d);
}

// ===== Bottom event timeline + era ribbon =====
const eraRibbonEl = document.getElementById('era-ribbon');
ERA_ORDER.forEach((era) => {
  const c = document.createElement('div');
  c.className = 'era-cell';
  c.style.background = ERA[era];
  c.textContent = era;
  c.dataset.era = era;
  c.onclick = () => {
    // toggle dim on the others
    const dim = !c.classList.contains('locked');
    eraRibbonEl.querySelectorAll('.era-cell').forEach(x => {
      x.classList.toggle('dim', dim && x.dataset.era !== era);
      x.classList.toggle('locked', dim && x.dataset.era === era);
    });
    filterTimelineByEra(dim ? era : null);
  };
  eraRibbonEl.appendChild(c);
});

const tlScroll = document.getElementById('timeline-scroll');
const tlEmpty = document.getElementById('tl-empty');
const evCards = [];
if (DATA.timeline.length > 0) {
  tlEmpty.remove();
  for (const e of DATA.timeline) {
    const d = document.createElement('div');
    d.className = 'evt' + (e.severity ? ' sev-' + e.severity : '') + (e.kind === 'lore' ? ' kind-lore' : '');
    d.dataset.era = e.era_tag || '';
    d.dataset.faction = e.faction_tag || '';
    const c = colorFor(e);
    d.style.borderLeftColor = c;
    d.innerHTML =
      `<div class="dt" style="color:${c};">${escapeHtml(e.date || '')}` +
      (e.severity ? ` <span style="color:var(--gold); font-size:10px;">★${e.severity}</span>` : '') + `</div>` +
      `<div class="tt">${escapeHtml(e.title || e.kind || '')}</div>` +
      `<div class="sm">${escapeHtml(e.summary || '')}</div>` +
      `<div class="badges">${badgeHtml(e)}${srcBadgeHtml(e.source_kind)}</div>` +
      (e.site_label ? `<div class="where">@ ${escapeHtml(e.site_label)}</div>` : '');
    d.onclick = () => {
      if (e.site_slug) openDetail(e.site_slug);
    };
    tlScroll.appendChild(d);
    evCards.push({ ev: e, el: d });
  }
}

function filterTimelineByEra(_era) {
  // delegates to applyAllFilters which respects era ribbon locked state
  applyAllFilters();
}

// ===== Stats =====
document.getElementById('stat-sites').textContent  = DATA.counts.sites;
document.getElementById('stat-events').textContent = DATA.counts.events;
document.getElementById('stat-lore').textContent   = DATA.counts.lore;
document.getElementById('stat-chron').textContent  = DATA.counts.chronicle;
document.getElementById('stat-persons').textContent= DATA.counts.persons || 0;
document.getElementById('stat-src').textContent    = Object.keys(DATA.source_kind_counts || {}).length;
document.getElementById('stat-src-total').textContent = DATA.counts.sources_total || 0;

// ===== Inline SVG stat charts =====
const statChartsEl = document.getElementById('stat-charts');
const METRIC_LABEL = {
  members:      ['工藤會 構成員・準構成員(概数)', '人'],
  handguns:     ['福岡県内 拳銃押収数(概数)',     '丁'],
  warnings:     ['福岡県 中止命令件数(概数)',     '件'],
  advice_cases: ['暴追センター相談件数(概数)',   '件'],
  defectors:    ['暴追センター 離脱支援(概数)',  '件'],
};
const STAT_ANNOTS = {
  2012: '特定危険指定',
  2013: 'OFAC TCO 指定',
  2014: '頂上作戦',
  2019: '本部解体',
  2021: '一審判決',
  2024: '控訴審',
};

function renderStatChart(metric, pts) {
  if (!pts.length) return;
  const def = METRIC_LABEL[metric] || [metric, ''];
  const card = document.createElement('div');
  card.className = 'stat-card';
  const minYear = Math.min(...pts.map(p => p.year));
  const maxYear = Math.max(...pts.map(p => p.year));
  const minVal  = 0;
  const maxVal  = Math.max(...pts.map(p => p.value)) * 1.1;
  const W = 290, H = 100, ML = 30, MR = 10, MT = 8, MB = 16;
  const PW = W - ML - MR, PH = H - MT - MB;
  function x(y) { return ML + ((y - minYear) / Math.max(1, maxYear - minYear)) * PW; }
  function y(v) { return MT + PH - ((v - minVal) / Math.max(1, maxVal - minVal)) * PH; }
  const pathD = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(p.year).toFixed(1)} ${y(p.value).toFixed(1)}`).join(' ');
  // gridlines + axis labels
  let grid = '';
  for (let i = 0; i <= 4; i++) {
    const yPos = MT + (PH * i / 4);
    const val = (maxVal - (maxVal - minVal) * i / 4);
    grid += `<line class="gridline" x1="${ML}" y1="${yPos}" x2="${W - MR}" y2="${yPos}" />`;
    grid += `<text class="axis" x="${ML - 4}" y="${yPos + 3}" text-anchor="end">${Math.round(val)}</text>`;
  }
  // year axis ticks
  let ticks = '';
  for (let yr = Math.ceil(minYear / 5) * 5; yr <= maxYear; yr += 5) {
    ticks += `<text class="axis" x="${x(yr)}" y="${H - 2}" text-anchor="middle">${yr}</text>`;
    ticks += `<line class="gridline" x1="${x(yr)}" y1="${MT}" x2="${x(yr)}" y2="${MT + PH}" />`;
  }
  // annotation markers
  let annots = '';
  for (const yr in STAT_ANNOTS) {
    const y_int = parseInt(yr);
    if (y_int < minYear || y_int > maxYear) continue;
    annots += `<line x1="${x(y_int)}" y1="${MT}" x2="${x(y_int)}" y2="${MT + PH}" stroke="var(--accent2)" stroke-width="0.6" stroke-dasharray="2,2"/>`;
    annots += `<text class="annot" x="${x(y_int) + 2}" y="${MT + 8}">${STAT_ANNOTS[yr]}</text>`;
  }
  // line + dots
  const dots = pts.map(p =>
    `<circle class="dot" cx="${x(p.year).toFixed(1)}" cy="${y(p.value).toFixed(1)}" r="2"><title>${p.year}: ${p.value} ${p.unit || ''}</title></circle>`
  ).join('');
  const svg = `
    <svg width="100%" height="${H}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
      ${grid}
      ${ticks}
      ${annots}
      <path class="line" d="${pathD}" />
      ${dots}
    </svg>`;
  card.innerHTML =
    `<div class="tt">${escapeHtml(def[0])}</div>` +
    `<div class="sub">${pts.length} 年分 · ${minYear}–${maxYear} · 単位 ${escapeHtml(def[1])}</div>` +
    svg;
  statChartsEl.appendChild(card);
}
for (const m of ['members', 'handguns', 'warnings', 'advice_cases', 'defectors']) {
  if (DATA.crime_stats && DATA.crime_stats[m]) renderStatChart(m, DATA.crime_stats[m]);
}

// ===== Source-kind ribbon =====
const sourceRibbonEl = document.getElementById('source-chips');
const sourceFilter = new Set(); // empty = no filter
const counts = DATA.source_kind_counts || {};
const orderedKinds = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
for (const sk of orderedKinds) {
  const def = SRC_BADGE[sk];
  if (!def) continue;
  const [emoji, label, color] = def;
  const c = document.createElement('span');
  c.className = 'sb';
  c.style.borderColor = color;
  c.style.color = color;
  c.innerHTML = `${emoji} ${label} <span class="cnt">${counts[sk]}</span>`;
  c.onclick = () => {
    if (sourceFilter.has(sk)) { sourceFilter.delete(sk); c.classList.remove('active'); }
    else { sourceFilter.add(sk); c.classList.add('active'); }
    applyAllFilters();
  };
  sourceRibbonEl.appendChild(c);
}

function eventVisible(ev) {
  if (factionFilter.size > 0 && ev.faction_tag && !factionFilter.has(ev.faction_tag)) return false;
  if (sourceFilter.size > 0 && (!ev.source_kind || !sourceFilter.has(ev.source_kind))) return false;
  const lockedEra = eraRibbonEl.querySelector('.era-cell.locked')?.dataset.era;
  if (lockedEra && ev.era_tag !== lockedEra) return false;
  return true;
}
function applyAllFilters() {
  for (const c of evCards) {
    c.el.classList.toggle('hidden', !eventVisible(c.ev));
  }
}

// ===== Mode bar =====
function setMode(m) {
  colorMode = m;
  document.querySelectorAll('#modebar .chip.mode').forEach(c =>
    c.classList.toggle('active', c.dataset.mode === m));
  refreshMarkers();
  // re-render event card borders too
  for (const c of evCards) {
    const col = colorFor(c.ev);
    c.el.style.borderLeftColor = col;
    const dt = c.el.querySelector('.dt');
    if (dt) dt.style.color = col;
  }
  renderLegend();
}
document.querySelectorAll('#modebar .chip.mode').forEach(c => {
  c.onclick = () => setMode(c.dataset.mode);
});

// Faction filter chips
const factionChipsEl = document.getElementById('faction-chips');
FACTION_ORDER.forEach(f => {
  const c = document.createElement('span');
  c.className = 'chip';
  c.style.borderColor = FACTION[f];
  c.style.color = FACTION[f];
  c.textContent = f;
  c.onclick = () => {
    if (factionFilter.has(f)) { factionFilter.delete(f); c.classList.remove('active'); c.style.background = ''; c.style.color = FACTION[f]; }
    else { factionFilter.add(f); c.classList.add('active'); c.style.background = FACTION[f]; c.style.color = '#fff'; }
    refreshMarkers();
    filterTimelineByEra(eraRibbonEl.querySelector('.era-cell.locked')?.dataset.era || null);
  };
  factionChipsEl.appendChild(c);
});

// ===== Legend =====
const legendEl = document.getElementById('legend');
function renderLegend() {
  let h = '';
  if (colorMode === 'kind') {
    h += `<div class="title">凡例 — 種別</div>`;
    const items = [
      ['attack', '襲撃'], ['extortion', 'みかじめ要求'], ['arrest', '逮捕'],
      ['raid', '一斉摘発'], ['ruling', '判決'], ['demolition', '解体'],
      ['designation', '指定'], ['war', '抗争'], ['faction_split', '分裂'],
      ['lore', '軼話'],
    ];
    for (const [k, lbl] of items) {
      h += `<div class="row"><span class="sw" style="background:${KIND[k]};"></span>${lbl}</div>`;
    }
  } else if (colorMode === 'faction') {
    h += `<div class="title">凡例 — 派閥</div>`;
    for (const f of FACTION_ORDER) {
      h += `<div class="row"><span class="sw" style="background:${FACTION[f]};"></span>${f}</div>`;
    }
  } else if (colorMode === 'era') {
    h += `<div class="title">凡例 — 時代</div>`;
    for (const e of ERA_ORDER) {
      h += `<div class="row"><span class="sw" style="background:${ERA[e]};"></span>${e}</div>`;
    }
  }
  legendEl.innerHTML = h;
}
renderLegend();

// ===== Layer toggles =====
const togglePoi = document.getElementById('toggle-poi');
togglePoi.onchange = () => {
  for (const slug in siteIndex) {
    const rec = siteIndex[slug];
    if (togglePoi.checked) {
      for (const p of rec.site.poi || []) {
        const m = L.marker([p.lat, p.lon], {
          icon: L.divIcon({ className: '', html: '<div class="poi-pin"></div>', iconSize: [6,6] }),
          title: p.name || p.descr || p.type,
        }).bindTooltip(`${p.name || ''} <small>(${p.descr || ''})</small>`).addTo(map);
        rec.poiMarkers.push(m);
      }
    } else {
      for (const m of rec.poiMarkers) map.removeLayer(m);
      rec.poiMarkers.length = 0;
    }
  }
};
const toggleSat = document.getElementById('toggle-sat');
toggleSat.onchange = () => {
  if (toggleSat.checked) {
    map.removeLayer(osmLayer);
    esriLayer.addTo(map);
  } else {
    map.removeLayer(esriLayer);
    osmLayer.addTo(map);
  }
};

// ===== Splash entry — 5つの読み方 =====
function closeSplash() { document.getElementById('splash').style.display = 'none'; }
document.querySelectorAll('#splash .way').forEach(el => {
  el.onclick = () => {
    const way = el.dataset.way;
    closeSplash();
    if (way === 'hq') {
      setTimeout(() => openDetail('kudokai_hq_kandake'), 100);
    } else if (way === 'tour-chron') {
      runChronTour();
    } else if (way === 'tour-gossip') {
      setMode('faction');
      runGossipTour();
    } else if (way === 'cases-4') {
      runCases4Tour();
    } else if (way === 'map-free') {
      // just open the map, no auto detail
    }
  };
});
// (runCases4Tour is now defined above with the tour engine)

// ===== TOC + section collapse =====
document.querySelectorAll('#toc a[data-jump]').forEach(a => {
  a.onclick = (e) => {
    e.preventDefault();
    const target = document.getElementById(a.dataset.jump);
    if (target) {
      target.previousElementSibling.classList.remove('collapsed');
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };
});
document.querySelectorAll('#side h2[data-section]').forEach(h => {
  h.onclick = () => h.classList.toggle('collapsed');
});

// ===== Help overlay =====
const helpEl = document.getElementById('help-overlay');
document.getElementById('help-btn').onclick = () => helpEl.classList.add('show');
document.getElementById('close-help').onclick = () => helpEl.classList.remove('show');
helpEl.onclick = (e) => { if (e.target === helpEl) helpEl.classList.remove('show'); };

// Show help once on first visit — after splash is dismissed
function maybeShowFirstHelp() {
  if (localStorage.getItem('kokura_seen_help')) return;
  if (document.getElementById('splash').style.display === 'none') {
    helpEl.classList.add('show');
    localStorage.setItem('kokura_seen_help', '1');
  }
}
const _origClose = closeSplash;
closeSplash = function() { _origClose(); setTimeout(maybeShowFirstHelp, 500); };
// Re-attach since we redefined
document.querySelectorAll('#splash .way').forEach(el => {
  const way = el.dataset.way;
  el.onclick = () => {
    closeSplash();
    if (way === 'hq') setTimeout(() => openDetail('kudokai_hq_kandake'), 100);
    else if (way === 'tour-chron') runChronTour();
    else if (way === 'tour-gossip') { setMode('faction'); runGossipTour(); }
    else if (way === 'cases-4') runCases4Tour();
    else if (way === 'tour-menu') setTimeout(openTourMenu, 200);
  };
});

// ===== Mobile side panel toggle =====
const sideEl = document.getElementById('side');
function toggleSide() {
  sideEl.classList.toggle('open');
  if (sideEl.classList.contains('open')) detailEl.classList.remove('open');
}
document.getElementById('fab-menu')?.addEventListener('click', toggleSide);
sideEl.addEventListener('click', (e) => {
  if (e.target === sideEl) toggleSide();
});

// ===== Global search =====
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');

// Build search index once.
const searchIndex = [];
// Sites
for (const s of DATA.sites) {
  searchIndex.push({
    type: 'site', ico: '📍', label: s.label, sub: s.kind || '',
    extra: (s.notes || '') + ' ' + (s.place || ''),
    onclick: () => openDetail(s.slug),
  });
}
// Events
for (const e of DATA.timeline) {
  searchIndex.push({
    type: 'event', ico: '⚡', label: e.title || e.kind, sub: e.date || '',
    extra: (e.summary || '') + ' ' + (e.site_label || ''),
    onclick: () => { if (e.site_slug) openDetail(e.site_slug); },
  });
}
// Lore (highlight reel)
for (const l of (DATA.floating_lore || [])) {
  searchIndex.push({
    type: 'lore', ico: '🟡', label: l.title || '', sub: l.year || '',
    extra: l.body || '',
    onclick: () => { if (l.site_slug) openDetail(l.site_slug); },
  });
}
// Persons
for (const p of (DATA.persons || [])) {
  searchIndex.push({
    type: 'person', ico: '👤', label: p.name || '', sub: p.role || '',
    extra: (p.body || '') + ' ' + (p.name_kana || ''),
    onclick: () => { if (p.site_slug) openDetail(p.site_slug); },
  });
}
// Chronicle
for (const c of (DATA.chronicle || [])) {
  searchIndex.push({
    type: 'chronicle', ico: '📜', label: c.title || '', sub: c.year || '',
    extra: c.body || '',
    onclick: () => {
      // chronicle entry click handler in side panel — just open the matched site if any
      const target = matchChronToSite(c);
      if (target) openDetail(target);
    },
  });
}
// Tours
for (const cat of TOUR_CATEGORIES) {
  for (const t of cat.tours) {
    searchIndex.push({
      type: 'tour', ico: '🎬', label: t.title, sub: cat.name + ' / ' + t.steps.length + ' steps',
      extra: t.desc || '',
      onclick: () => startTour(t.steps),
    });
  }
}

const TYPE_LABEL = {
  site: '拠点',
  event: '事件',
  lore: '軼話',
  person: '人物',
  chronicle: '系譜',
  tour: 'ツアー',
};

function performSearch(q) {
  q = (q || '').trim().toLowerCase();
  if (!q) { searchResults.classList.remove('show'); return; }
  const hits = [];
  for (const item of searchIndex) {
    const haystack = (item.label + ' ' + item.sub + ' ' + (item.extra || '')).toLowerCase();
    if (haystack.includes(q)) {
      // simple score: prefer label hits, then short distance
      const labelHit = item.label.toLowerCase().includes(q);
      hits.push({ ...item, _score: labelHit ? 1 : 2 });
    }
  }
  hits.sort((a, b) => a._score - b._score);
  // Group by type
  const groups = {};
  for (const h of hits) {
    if (!groups[h.type]) groups[h.type] = [];
    if (groups[h.type].length < 8) groups[h.type].push(h);  // cap per type
  }
  const html = [];
  if (Object.keys(groups).length === 0) {
    html.push(`<div class="empty">該当なし</div>`);
  } else {
    const order = ['site', 'event', 'lore', 'person', 'tour', 'chronicle'];
    for (const t of order) {
      if (!groups[t]) continue;
      html.push(`<div class="group">${TYPE_LABEL[t]} (${groups[t].length})</div>`);
      for (const h of groups[t]) {
        html.push(
          `<div class="hit" data-idx="${searchIndex.indexOf(h)}">` +
            `<span class="ico">${h.ico}</span>` +
            `<span class="lbl">${escapeHtml(h.label)}</span>` +
            (h.sub ? `<span class="sub">${escapeHtml(h.sub)}</span>` : '') +
          `</div>`
        );
      }
    }
  }
  searchResults.innerHTML = html.join('\n');
  searchResults.classList.add('show');
  // Wire click handlers
  searchResults.querySelectorAll('.hit').forEach(el => {
    const idx = parseInt(el.dataset.idx);
    el.onclick = () => {
      searchIndex[idx].onclick();
      searchResults.classList.remove('show');
      searchInput.value = '';
      searchInput.blur();
    };
  });
}

let searchTimer = null;
searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => performSearch(searchInput.value), 100);
});
searchInput.addEventListener('focus', () => {
  if (searchInput.value) performSearch(searchInput.value);
});
// Hide results when clicking outside
document.addEventListener('click', (e) => {
  if (!e.target.closest('#search-wrap')) {
    searchResults.classList.remove('show');
  }
});
// Esc closes
searchInput.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    searchInput.value = '';
    searchResults.classList.remove('show');
    searchInput.blur();
  }
});

// ===== Mobile filter modal =====
const filterModal = document.getElementById('filter-modal');
const mModes = document.getElementById('m-modes');
const mFactions = document.getElementById('m-factions');
const mSources = document.getElementById('m-sources');
const mEras = document.getElementById('m-eras');

function openFilterModal() { filterModal.classList.add('show'); }
function closeFilterModal() { filterModal.classList.remove('show'); }
document.getElementById('fab-filter')?.addEventListener('click', openFilterModal);
document.getElementById('close-filter')?.addEventListener('click', closeFilterModal);

// Populate mobile filter chips, mirror desktop state
mModes.querySelectorAll('.chip').forEach(c => {
  c.onclick = () => {
    setMode(c.dataset.mode);
    mModes.querySelectorAll('.chip').forEach(x => x.classList.toggle('active', x === c));
  };
});
FACTION_ORDER.forEach(f => {
  const c = document.createElement('span');
  c.className = 'chip';
  c.style.borderColor = FACTION[f];
  c.style.color = FACTION[f];
  c.textContent = f;
  c.onclick = () => {
    if (factionFilter.has(f)) { factionFilter.delete(f); c.classList.remove('active'); }
    else { factionFilter.add(f); c.classList.add('active'); }
    refreshMarkers();
    applyAllFilters();
    // also sync desktop chips
    document.querySelectorAll('#faction-chips .chip').forEach(dc => {
      if (dc.textContent === f) dc.classList.toggle('active', factionFilter.has(f));
    });
  };
  mFactions.appendChild(c);
});
const orderedKindsForMobile = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
orderedKindsForMobile.forEach(sk => {
  const def = SRC_BADGE[sk]; if (!def) return;
  const [emoji, label, color] = def;
  const c = document.createElement('span');
  c.className = 'chip'; c.style.borderColor = color; c.style.color = color;
  c.innerHTML = `${emoji} ${label}`;
  c.onclick = () => {
    if (sourceFilter.has(sk)) { sourceFilter.delete(sk); c.classList.remove('active'); }
    else { sourceFilter.add(sk); c.classList.add('active'); }
    applyAllFilters();
  };
  mSources.appendChild(c);
});
ERA_ORDER.forEach(era => {
  const c = document.createElement('span');
  c.className = 'chip'; c.style.borderColor = ERA[era]; c.style.color = ERA[era];
  c.textContent = era;
  let locked = false;
  c.onclick = () => {
    locked = !locked;
    mEras.querySelectorAll('.chip').forEach(x => x.classList.remove('active'));
    if (locked) {
      c.classList.add('active');
      // sync the desktop era ribbon
      eraRibbonEl.querySelectorAll('.era-cell').forEach(x => {
        x.classList.toggle('dim', x.dataset.era !== era);
        x.classList.toggle('locked', x.dataset.era === era);
      });
    } else {
      eraRibbonEl.querySelectorAll('.era-cell').forEach(x => {
        x.classList.remove('dim'); x.classList.remove('locked');
      });
    }
    applyAllFilters();
  };
  mEras.appendChild(c);
});

// ===== Timeline 4-state toggle =====
// Cycle: hidden → cards → exp → min → hidden
// Simple arrow icon shows direction of next state.
const timelineEl = document.getElementById('timeline');
const TL_STATES = ['hidden', 'cards', 'exp', 'min'];
// Icon = the arrow that hints at what next tap will do
const TL_ICONS = {
  hidden: '▼',  // tap to OPEN (show cards)
  cards:  '▼',  // tap to expand MORE
  exp:    '▲',  // tap to shrink (to min)
  min:    '▲',  // tap to hide
};
const TL_STORAGE_KEY = 'kokura_timeline_state_v2';
const _isMobileForTl = window.matchMedia('(max-width: 720px)').matches;
const _savedTl = localStorage.getItem(TL_STORAGE_KEY);
let tlStateIdx = (_savedTl && TL_STATES.includes(_savedTl))
  ? TL_STATES.indexOf(_savedTl)
  : (_isMobileForTl ? 0 /* hidden */ : 1 /* cards */);
function applyTimelineState() {
  const state = TL_STATES[tlStateIdx];
  document.body.classList.remove('timeline-cards', 'timeline-exp', 'timeline-min', 'timeline-hidden');
  document.body.classList.add('timeline-' + state);
  const tab = document.getElementById('timeline-expand-tab');
  if (tab) tab.textContent = TL_ICONS[state];
  try { localStorage.setItem(TL_STORAGE_KEY, state); } catch (e) {}
}
// Inline onclick attribute calls this; also attach via JS as backup.
function cycleTimelineState() {
  tlStateIdx = (tlStateIdx + 1) % TL_STATES.length;
  applyTimelineState();
}
window.cycleTimelineState = cycleTimelineState;

// ===== FAB button global handlers (called from inline onclick) =====
// Defined here at the end of JS so all dependencies are in scope.
window.fabTour = function() {
  try { openTourMenu(); } catch (e) { console.error('fabTour:', e); }
};
window.fabFilter = function() {
  try { openFilterModal(); } catch (e) { console.error('fabFilter:', e); }
};
window.fabMenu = function() {
  try { toggleSide(); } catch (e) { console.error('fabMenu:', e); }
};
window.fabHelp = function() {
  try { helpEl.classList.add('show'); } catch (e) { console.error('fabHelp:', e); }
};
window.fabPoi = function() {
  try {
    const cb = document.getElementById('toggle-poi');
    cb.checked = !cb.checked;
    cb.dispatchEvent(new Event('change'));
    const btn = document.getElementById('fab-poi');
    if (btn) btn.style.background = cb.checked ? '#d9534f' : '#9aa6b2';
  } catch (e) { console.error('fabPoi:', e); }
};
window.fabSat = function() {
  try {
    const cb = document.getElementById('toggle-sat');
    cb.checked = !cb.checked;
    cb.dispatchEvent(new Event('change'));
    const btn = document.getElementById('fab-sat');
    if (btn) btn.style.background = cb.checked ? '#d9534f' : '#34495e';
  } catch (e) { console.error('fabSat:', e); }
};
// Backup event listener (in case inline onclick is blocked)
const _tabEl = document.getElementById('timeline-expand-tab');
if (_tabEl) {
  _tabEl.addEventListener('click', cycleTimelineState);
  _tabEl.addEventListener('touchend', (e) => { e.preventDefault(); cycleTimelineState(); }, { passive: false });
}
applyTimelineState();

// ===== Marker thinning at low zoom (mobile) =====
// At zoom < 14 (wide view), show only HQ + major attack sites, not all 89 markers
const MAJOR_KINDS = new Set(['hq_former', 'hq_current', 'attack_site', 'landmark']);
function applyZoomThinning() {
  if (!window.matchMedia('(max-width: 720px)').matches) return;
  const z = map.getZoom();
  const showAll = z >= 14;
  for (const slug in siteIndex) {
    const rec = siteIndex[slug];
    const isMajor = MAJOR_KINDS.has(rec.site.kind);
    const inFilter = factionFilter.size === 0 ||
                     (rec.site.faction_tag && factionFilter.has(rec.site.faction_tag));
    if (!inFilter) {
      if (map.hasLayer(rec.marker)) map.removeLayer(rec.marker);
      continue;
    }
    const shouldShow = showAll || isMajor;
    if (shouldShow && !map.hasLayer(rec.marker)) map.addLayer(rec.marker);
    else if (!shouldShow && map.hasLayer(rec.marker)) map.removeLayer(rec.marker);
  }
}
map.on('zoomend moveend', applyZoomThinning);
applyZoomThinning();

const banner = document.getElementById('tour-banner');
function showBanner(text, dwell = 2500) {
  banner.textContent = text;
  banner.classList.add('show');
  setTimeout(() => banner.classList.remove('show'), dwell);
}

// ===== Controllable tour engine =====
// A "step" is a flat list of {slug, banner?}. We flatten chapter-based tours
// into a single sequence so prev/next/pause work uniformly.
const tour = {
  steps: [],        // [{slug, banner?, label?}]
  idx: 0,
  paused: false,
  timer: null,
  stepDurationMs: 6500,
};

const tourCtrls = document.getElementById('tour-controls');
const tourPlayBtn = tourCtrls.querySelector('.play-pause');
const tourPrevBtn = tourCtrls.querySelector('.prev');
const tourNextBtn = tourCtrls.querySelector('.next');
const tourStopBtn = tourCtrls.querySelector('.stop');
const tourPosEl = document.getElementById('tour-pos');
const tourLabelEl = document.getElementById('tour-label');

function tourClearTimer() { if (tour.timer) { clearTimeout(tour.timer); tour.timer = null; } }
function tourShow() { tourCtrls.classList.add('show'); updateTourUI(); }
function tourHide() {
  tourClearTimer();
  tour.steps = []; tour.idx = 0; tour.paused = false;
  tourCtrls.classList.remove('show');
  document.body.classList.remove('tour-active');
}
function updateTourUI() {
  if (tour.steps.length === 0) return;
  tourPosEl.textContent = `${tour.idx + 1} / ${tour.steps.length}`;
  const step = tour.steps[tour.idx];
  tourLabelEl.textContent = step.label || siteIndex[step.slug]?.site?.label || '';
  tourPlayBtn.textContent = tour.paused ? '▶' : '⏸';
  tourPlayBtn.title = tour.paused ? '再生' : '一時停止';
}
function tourGoTo(idx) {
  tourClearTimer();
  if (idx < 0 || idx >= tour.steps.length) { tourHide(); return; }
  tour.idx = idx;
  const step = tour.steps[idx];
  if (step.banner) showBanner(step.banner, 3000);
  const rec = siteIndex[step.slug];
  if (rec) {
    map.flyTo([rec.site.lat, rec.site.lon], 17, { duration: 1.6 });
    setTimeout(() => openDetail(step.slug), 1700);
  }
  updateTourUI();
  if (!tour.paused) {
    tour.timer = setTimeout(() => {
      if (tour.idx < tour.steps.length - 1) tourGoTo(tour.idx + 1);
      else tourHide();
    }, tour.stepDurationMs);
  }
}
function startTour(steps) {
  tourClearTimer();
  tour.steps = steps;
  tour.idx = 0;
  tour.paused = false;
  document.body.classList.add('tour-active');
  // close tour menu if open
  document.getElementById('tour-menu')?.classList.remove('show');
  tourShow();
  tourGoTo(0);
}

// ===== Tour catalog (組織系統別、各ツアー 7-15 ステップで深掘り) =====
const TOUR_CATEGORIES = [
  {
    name: '工藤會 / 北九州',
    color: '#d9534f',
    tours: [
      { id: 'hq_focus', title: '本部跡から始める', desc: '神岳1丁目の「金看板」から解体、跡地問題まで',
        steps: [
          { slug: 'kudokai_hq_kandake', banner: '神岳1丁目 — 工藤會本部跡' },
          { slug: 'kandake_intersection' },
          { slug: 'kudokai_hq_kandake_signboard' },
          { slug: 'majaku_district' },
          { slug: 'ogura_keisatsu' },
          { slug: 'kokurakita_police_station2' },
          { slug: 'fukuoka_kenkei' },
          { slug: 'kokura_district_court' },
          { slug: 'kokura_bouhai_office' },
          { slug: 'kitakyushu_city_council' },
        ]},
      { id: 'chron_5acts', title: '系譜順 5幕(戦後→解体後)', desc: '1901 八幡製鐵所→2024 控訴審まで全 15 ステップ',
        steps: [
          { slug: 'yawata_seitetsu_1901', banner: '第1幕 ─ 重工業都市の前史(1901-)' },
          { slug: 'kokura_yamiichi_1946' },
          { slug: 'kusano_ikka_origin_kokura' },
          { slug: 'kudogumi_nakatsu_origin' },
          { slug: 'uomachi_arcade' },
          { slug: 'yamaguchigumi_kyushu_entry', banner: '第2幕 ─ 神岳に本部が立つ(1980s)' },
          { slug: 'kudokai_hq_kandake' },
          { slug: 'ogura_keisatsu' },
          { slug: 'heisei_shinten_chi', banner: '第3幕 ─ 市民への威迫(2000–2014)' },
          { slug: 'attack_1998_ashiya_fisheries' },
          { slug: 'attack_2012_ex_officer' },
          { slug: 'attack_2013_nurse' },
          { slug: 'attack_2014_dentist' },
          { slug: 'fukuoka_kenkei', banner: '第4幕 ─ 頂上作戦と解体(2014–2021)' },
          { slug: 'kudokai_hq_kandake_signboard' },
          { slug: 'kokura_district_court' },
          { slug: 'tanga_market', banner: '第5幕 ─ その後の街・トクリュウへ(2022–)' },
          { slug: 'bouhai_center_fukuoka' },
          { slug: 'komae_robbery_2023' },
        ]},
      { id: 'cases4', title: '市民襲撃4事件 + 公判', desc: '1998-2014 事件発生地 + 公判会場',
        steps: [
          { slug: 'attack_1998_ashiya_fisheries', banner: '市民襲撃4事件 — 1998 元漁協理事射殺' },
          { slug: 'attack_2012_ex_officer' },
          { slug: 'mihagino_district' },
          { slug: 'attack_2013_nurse' },
          { slug: 'attack_2014_dentist' },
          { slug: 'fukuoka_kenkei' },
          { slug: 'kudokai_hq_kandake' },
          { slug: 'kokura_district_court' },
        ]},
      { id: 'kudokai_legal', title: '頂上作戦から OFAC まで(法制度)', desc: '2014 逮捕→2024 控訴審 + 国際金融制裁',
        steps: [
          { slug: 'fukuoka_kenkei', banner: '頂上作戦 — 県警組織犯罪対策課' },
          { slug: 'kudokai_hq_kandake' },
          { slug: 'kudokai_hq_kandake_signboard' },
          { slug: 'kokura_district_court' },
          { slug: 'tokyo_npa_hq' },
          { slug: 'kokkai_diet_tokyo' },
          { slug: 'ofac_treasury_designation' },
          { slug: 'tokyo_us_embassy' },
          { slug: 'fukuoka_pref_assembly' },
        ]},
      { id: 'after_demolish', title: '解体後の街 + 暴排運動', desc: '本部跡・旦過火災・市民側の街づくり',
        steps: [
          { slug: 'kudokai_hq_kandake', banner: '2019-07-04 解体着工日' },
          { slug: 'kandake_intersection' },
          { slug: 'tanga_market', banner: '2022 旦過市場 二度の大火' },
          { slug: 'uomachi_kawazoi' },
          { slug: 'uomachi_arcade' },
          { slug: 'sakaimachi_quarter' },
          { slug: 'sunatsu_business_area' },
          { slug: 'bouhai_center_fukuoka' },
          { slug: 'kokurakita_police_station2' },
          { slug: 'kitakyushu_city_council' },
          { slug: 'wasshoi_summer_festival' },
        ]},
      { id: 'walking_kokura', title: '小倉北区街歩き', desc: '13 拠点を地理順に巡る街歩きルート',
        steps: [
          { slug: 'kokura_station', banner: '小倉駅 — 出発点' },
          { slug: 'komemachi_arcade' },
          { slug: 'chuocho_center' },
          { slug: 'uomachi_arcade' },
          { slug: 'tanga_market' },
          { slug: 'sakaimachi_quarter' },
          { slug: 'kyomachi_quarter' },
          { slug: 'horumon_district_sakaimachi' },
          { slug: 'muromachi_arcade' },
          { slug: 'kandake_intersection' },
          { slug: 'kudokai_hq_kandake' },
          { slug: 'majaku_district' },
          { slug: 'ogura_keisatsu' },
        ]},
    ]
  },
  {
    name: '九州抗争 / 久留米',
    color: '#9b59b6',
    tours: [
      { id: 'dojin_genealogy', title: '道仁会・誠道会・浪川会 系譜', desc: '1971 結成→2006 分派→2013 再編 + 周辺都市',
        steps: [
          { slug: 'kurume_dojinkai_main_hq', banner: '道仁会 — 1971 久留米結成' },
          { slug: 'kurume_seidokai_hq' },
          { slug: 'kurume_namikawakai_hq' },
          { slug: 'kurume_bunkagai_central' },
          { slug: 'kurume_west_arcade' },
          { slug: 'kurume_keisatsu' },
          { slug: 'kurume_shrine_temple' },
        ]},
      { id: 'kyushu_war', title: '九州抗争 2006-2013 全 10 ステップ', desc: '7年間の地理的拡散と市民生活への影響',
        steps: [
          { slug: 'kurume_seidokai_hq', banner: '九州抗争 — 2006 道仁会内紛から' },
          { slug: 'kurume_bunkagai_central' },
          { slug: 'kurume_dojinkai_main_hq' },
          { slug: 'amagi_periphery' },
          { slug: 'arao_omuta' },
          { slug: 'omuta_dojin_relation' },
          { slug: 'saga_periphery_kyushu_war' },
          { slug: 'kurume_keisatsu' },
          { slug: 'kurume_namikawakai_hq' },
          { slug: 'kurume_jr_station' },
        ]},
      { id: 'kyushu_jiba', title: '九州地場連合 — 5 系統並列', desc: '工藤會 / 道仁会 / 浪川会 / 太州会 / 福博会',
        steps: [
          { slug: 'kudokai_hq_kandake', banner: '九州地場 5 系統並列' },
          { slug: 'kurume_dojinkai_main_hq' },
          { slug: 'kurume_namikawakai_hq' },
          { slug: 'tagawa_taishu_hq' },
          { slug: 'kasuga_fukuhakukai' },
          { slug: 'compare_namikawakai_hq' },
        ]},
    ]
  },
  {
    name: '山口組史 / 神戸',
    color: '#8e44ad',
    tours: [
      { id: 'yamaguchi_110years', title: '山口組 110 年史 全 10 ステップ', desc: '1915 結成→田岡→山一抗争→神戸分裂→絆會',
        steps: [
          { slug: 'kobe_yamaguchi_origin', banner: '1915 山口春吉 神戸港' },
          { slug: 'kobe_yamaguchi_souhonbu' },
          { slug: 'kobe_geinosha' },
          { slug: 'osaka_yamaguchi_kizunabashi' },
          { slug: 'shinobu_tsukasa_kobe' },
          { slug: 'kobe_yamaichi_ground_zero' },
          { slug: 'nagoya_kodokai_hq' },
          { slug: 'kobe_kobeyamaguchigumi_hq' },
          { slug: 'kobe_kizunakai_hq' },
          { slug: 'hyogo_keisatsu_hq' },
        ]},
      { id: 'yamaichi_war', title: '山一抗争 1985-1989 + 暴対法成立', desc: '5 年 300 事件 → 1991 暴対法の最大背景',
        steps: [
          { slug: 'kobe_yamaichi_ground_zero', banner: '山一抗争 — 1985-08-27 分裂から' },
          { slug: 'kobe_yamaguchi_souhonbu' },
          { slug: 'osaka_yamaguchi_kizunabashi' },
          { slug: 'hyogo_keisatsu_hq' },
          { slug: 'bubble_jiage' },
          { slug: 'tokyo_diet_again' },
          { slug: 'kokkai_diet_tokyo' },
        ]},
      { id: 'kobe_split', title: '神戸山口組分裂 2015-2024 全 8 ステップ', desc: '六代目→神戸→任侠→絆會 三派対立から特定抗争指定解除まで',
        steps: [
          { slug: 'kobe_yamaguchi_souhonbu', banner: '2015 神戸山口組分裂' },
          { slug: 'kobe_kobeyamaguchigumi_hq' },
          { slug: 'kobe_kizunakai_hq' },
          { slug: 'shinobu_tsukasa_kobe' },
          { slug: 'hyogo_keisatsu_hq' },
          { slug: 'nagoya_kodokai_hq' },
          { slug: 'tokyo_npa_hq' },
          { slug: 'kansai_quake_yamaguchi' },
        ]},
      { id: 'kansai_yakuza', title: '関西ヤクザ 地場集中地', desc: '神戸・大阪ミナミ・キタ・釜ヶ崎・京都祇園',
        steps: [
          { slug: 'kobe_yamaguchi_souhonbu', banner: '関西地場 — 神戸から大阪・京都へ' },
          { slug: 'osaka_yamaguchi_kizunabashi' },
          { slug: 'osaka_minami_yakuza' },
          { slug: 'osaka_kita_yakuza' },
          { slug: 'osaka_kamagasaki' },
          { slug: 'kyoto_aizukotetsu_hq' },
          { slug: 'kyoto_gion' },
        ]},
    ]
  },
  {
    name: '半グレ・トクリュウ',
    color: '#ff6b35',
    tours: [
      { id: 'kanto_rengo', title: '関東連合の興亡(2010-2014)', desc: '海老蔵事件→六本木襲撃→解散→OB ネットワーク',
        steps: [
          { slug: 'kanto_rengo_hq', banner: '関東連合 — 2000年代の半グレ' },
          { slug: 'roppongi_clubs_hangure' },
          { slug: 'roppongi_flower_attack' },
          { slug: 'shinjuku_chaika_hangure' },
          { slug: 'tokyo_kabukicho' },
          { slug: 'shibuya_halloween_arrest' },
          { slug: 'doragon_chinese_hangure' },
          { slug: 'hangure_yokohama_chinatown' },
          { slug: 'kanto_rengo_ob_network' },
        ]},
      { id: 'luffy_full', title: 'ルフィ事件 全過程', desc: '狛江→フィリピン送還→4 人被告→警察庁トクリュウ対策',
        steps: [
          { slug: 'komae_robbery_2023', banner: 'ルフィ事件 — 2023-01-19 狛江強盗殺人' },
          { slug: 'kanagawa_yokohama_robbery' },
          { slug: 'philippines_luffy_base' },
          { slug: 'tokyo_metro_keisatsu' },
          { slug: 'cambodia_compounds_link' },
          { slug: 'telegram_yamiarbeit' },
          { slug: 'npa_tokuryu_office' },
          { slug: 'tokyo_sns_recruiter_office' },
        ]},
      { id: 'kanto_robberies', title: '関東広域連続強盗 2023-2024 全 12 ステップ', desc: '1都8県+関西・中部・東北への拡散',
        steps: [
          { slug: 'komae_robbery_2023', banner: '関東広域連続強盗 — 1都8県+全国拡散' },
          { slug: 'kanagawa_yokohama_robbery' },
          { slug: 'chiba_isumi_robbery' },
          { slug: 'saitama_warabi_robbery' },
          { slug: 'ibaraki_chikusei_robbery' },
          { slug: 'tochigi_oyama_robbery' },
          { slug: 'takasaki_gunma_robbery' },
          { slug: 'niigata_robbery_2024' },
          { slug: 'aichi_nagoya_robbery' },
          { slug: 'osaka_robbery_tokuryu' },
          { slug: 'hyogo_robbery_2024' },
          { slug: 'fukuoka_robbery_2024' },
        ]},
      { id: 'tokuryu_intl', title: 'トクリュウ国際拠点+規制', desc: 'フィリピン→カンボジア→SNS 募集→警察庁対策',
        steps: [
          { slug: 'philippines_luffy_base', banner: 'トクリュウ国際拠点' },
          { slug: 'cambodia_compounds_link' },
          { slug: 'intl_mekong_compounds_ref' },
          { slug: 'telegram_yamiarbeit' },
          { slug: 'special_fraud_callcenter' },
          { slug: 'roman_sagi_online' },
          { slug: 'npa_tokuryu_office' },
          { slug: 'tokyo_sns_recruiter_office' },
          { slug: 'osaka_sns_recruiter' },
        ]},
      { id: 'hangure_origin', title: '半グレ起源と歌舞伎町', desc: '暴走族→関東連合→怒羅権→渋谷→歌舞伎町の系譜',
        steps: [
          { slug: 'hangure_tokuryu_origin_culture', banner: '半グレ — 戦後不良文化の延長' },
          { slug: 'kanto_rengo_hq' },
          { slug: 'doragon_chinese_hangure' },
          { slug: 'roppongi_clubs_hangure' },
          { slug: 'tokyo_kabukicho' },
          { slug: 'shinjuku_chaika_hangure' },
          { slug: 'shibuya_halloween_arrest' },
          { slug: 'hangure_yokohama_chinatown' },
        ]},
    ]
  },
  {
    name: '全国・国際比較',
    color: '#16a085',
    tours: [
      { id: 'big_orgs', title: '日本の指定暴力団 — 主要 8 組織', desc: '山口組・住吉会・稲川会・工藤會・会津小鉄・浪川・共政・旭琉',
        steps: [
          { slug: 'kobe_yamaguchi_souhonbu', banner: '指定暴力団 主要 8 組織 — 全国の縄張り' },
          { slug: 'tokyo_sumiyoshi_hq' },
          { slug: 'tokyo_inagawakai_hq' },
          { slug: 'kudokai_hq_kandake' },
          { slug: 'compare_aizukotetsu_hq' },
          { slug: 'compare_namikawakai_hq' },
          { slug: 'hiroshima_kyoseikai_hq' },
          { slug: 'okinawa_kyokuryukai_main' },
        ]},
      { id: 'world_compare', title: '国際比較 — 世界の組織犯罪 9 拠点', desc: 'マフィア・LCN・三合会・コンパウンド・日本',
        steps: [
          { slug: 'intl_cosa_nostra_italy', banner: '国際比較 — 世界の組織犯罪' },
          { slug: 'intl_ndrangheta_italy' },
          { slug: 'intl_triads_hk' },
          { slug: 'intl_la_cosa_nostra_us' },
          { slug: 'intl_mekong_compounds_ref' },
          { slug: 'cambodia_compounds_link' },
          { slug: 'philippines_luffy_base' },
          { slug: 'kudokai_hq_kandake' },
          { slug: 'ofac_treasury_designation' },
        ]},
      { id: 'regulation_30y', title: '反社規制 30 年史(1991→2024)', desc: '暴対法→特定危険指定→OFAC→金融→トクリュウ対策',
        steps: [
          { slug: 'tokyo_diet_again', banner: '反社規制 30 年 — 1991 暴対法から' },
          { slug: 'kokkai_diet_tokyo' },
          { slug: 'tokyo_npa_hq' },
          { slug: 'ofac_treasury_designation' },
          { slug: 'tokyo_us_embassy' },
          { slug: 'mizuho_bank_hq' },
          { slug: 'tokyo_fsa' },
          { slug: 'zenginkyo_compliance' },
          { slug: 'fukuoka_pref_assembly' },
          { slug: 'bouhai_center_fukuoka' },
          { slug: 'npa_tokuryu_office' },
        ]},
      { id: 'finance_war', title: '金融・反社対応の30年', desc: '2007 指針→2011 標準化→2013 みずほ→2018 暗号資産→2024 トクリュウ',
        steps: [
          { slug: 'zenginkyo_compliance', banner: '銀行業界 反社対応 30 年' },
          { slug: 'mizuho_bank_hq' },
          { slug: 'tokyo_fsa' },
          { slug: 'tokyo_finance_district' },
          { slug: 'tokyo_us_embassy' },
          { slug: 'ofac_treasury_designation' },
          { slug: 'npa_tokuryu_office' },
        ]},
    ]
  },
  {
    name: '歴史・カルチャー',
    color: '#f1c40f',
    tours: [
      { id: 'postwar_yamiichi', title: '戦後闇市 1945-1955 全 9 ステップ', desc: '原爆代替標的→闇市→三国人事件→草野一家',
        steps: [
          { slug: 'kokura_air_raid_1945', banner: '戦後闇市 — 1945-08-09 から' },
          { slug: 'kokura_yamiichi_1946' },
          { slug: 'postwar_sanguokujin' },
          { slug: 'kusano_ikka_origin_kokura' },
          { slug: 'kudogumi_nakatsu_origin' },
          { slug: 'yawata_iron_works_area' },
          { slug: 'moji_kanmon_line' },
          { slug: 'uomachi_arcade' },
          { slug: 'kokura_yatai_corner' },
        ]},
      { id: 'yakuza_culture', title: 'ヤクザ表象の歴史 全 10 ステップ', desc: '仁義なき戦い→クローズ→ブラディドール→龍が如く→孤狼の血',
        steps: [
          { slug: 'hiroshima_jingi_movie', banner: 'ヤクザ表象 — 仁義なき戦い (1973-74)' },
          { slug: 'kobe_geinosha' },
          { slug: 'misora_hibari_taoka' },
          { slug: 'crows_kitakyu_setting' },
          { slug: 'mojiport_kitagata_book' },
          { slug: 'hiroshima_korou_no_chi' },
          { slug: 'ryugagotoku_virtual' },
          { slug: 'tokyo_kabukicho' },
          { slug: 'magazine_tsukuru' },
          { slug: 'jitsuwa_magazines' },
        ]},
      { id: 'kokura_two_atoms', title: '小倉と長崎の運命 + 北九州前史', desc: '1901 八幡製鐵→1945 原爆代替標的→闇市',
        steps: [
          { slug: 'yawata_seitetsu_1901', banner: '北九州前史 — 1901 八幡製鐵所から' },
          { slug: 'kokura_air_raid_1945' },
          { slug: 'hiroshima_atomic_park' },
          { slug: 'kokura_yamiichi_1946' },
          { slug: 'yawata_iron_works_area' },
          { slug: 'moji_kanmon_line' },
        ]},
      { id: 'sengo_kosei', title: '戦後初期抗争(1946-1965)', desc: '三国人事件→本多会抗争→山口組全国化',
        steps: [
          { slug: 'postwar_sanguokujin', banner: '戦後初期抗争 1946-1965' },
          { slug: 'kokura_yamiichi_1946' },
          { slug: 'kobe_yamaguchi_origin' },
          { slug: 'honda_kai_war' },
          { slug: 'kobe_yamaguchi_souhonbu' },
          { slug: 'osaka_yamaguchi_kizunabashi' },
        ]},
    ]
  },
  {
    name: 'テーマ深掘り',
    color: '#27ae60',
    tours: [
      { id: 'economy_bubble', title: '経済ヤクザ・バブル期', desc: '地上げ→住専→阪神大震災→みずほ事件',
        steps: [
          { slug: 'bubble_jiage', banner: '経済ヤクザ — バブル期から平成不良債権' },
          { slug: 'jusen_jutaku' },
          { slug: 'kansai_quake_yamaguchi' },
          { slug: 'mizuho_bank_hq' },
          { slug: 'tokyo_finance_district' },
          { slug: 'tokyo_fsa' },
          { slug: 'zenginkyo_compliance' },
        ]},
      { id: 'entertainment_yakuza', title: '芸能とヤクザ — 神戸芸能社時代', desc: '田岡一雄×美空ひばり→1989解散→暴排',
        steps: [
          { slug: 'kobe_geinosha', banner: '神戸芸能社 — 1957 設立から 1989 解散' },
          { slug: 'misora_hibari_taoka' },
          { slug: 'koshienjo_yakuza' },
          { slug: 'kobe_yamaguchi_souhonbu' },
          { slug: 'tokyo_kabukicho' },
        ]},
      { id: 'politics_yakuza', title: '政治とヤクザ — 児玉誉士夫からロッキードまで', desc: '戦後フィクサー→ロッキード→田中角栄判決',
        steps: [
          { slug: 'kodama_yoshio_residence', banner: '政治とヤクザ — 児玉誉士夫の戦後' },
          { slug: 'lockheed_scandal' },
          { slug: 'tokyo_diet_again' },
          { slug: 'kokkai_diet_tokyo' },
          { slug: 'tokyo_metro_keisatsu' },
        ]},
      { id: 'sports_yakuza', title: 'スポーツとヤクザ — 黒い霧から相撲八百長まで', desc: '1969プロ野球→2010大相撲野球賭博→2011八百長',
        steps: [
          { slug: 'proyakyu_kuroikiri', banner: 'スポーツとヤクザ — 1969 黒い霧から' },
          { slug: 'sumo_yakyu_baqto' },
          { slug: 'sumo_yaocho_2011' },
          { slug: 'koshienjo_yakuza' },
        ]},
      { id: 'drug_economy', title: '薬物経済 — 戦後70年史', desc: 'ヒロポン→指定暴力団→危険ドラッグ→SNS流通',
        steps: [
          { slug: 'hiropon_first_wave', banner: '薬物経済 — 戦後 70 年' },
          { slug: 'hiropon_second_wave' },
          { slug: 'iranian_dealers_shibuya' },
          { slug: 'cannabis_route_history' },
          { slug: 'dangerous_drugs_zone' },
          { slug: 'drug_meth_2019_yokohama' },
          { slug: 'drug_telegram_market' },
          { slug: 'drug_2020s_busts' },
        ]},
      { id: 'drug_routes', title: '薬物 国際密輸ルート', desc: '韓国・北朝鮮 → 中国・東南アジア → ゴールデントライアングル',
        steps: [
          { slug: 'drug_korea_route', banner: '薬物 国際密輸ルート' },
          { slug: 'drug_china_southeast' },
          { slug: 'myanmar_compounds_link' },
          { slug: 'cambodia_compounds_link' },
          { slug: 'thailand_tokuryu_base' },
          { slug: 'drug_meth_2019_yokohama' },
        ]},
      { id: 'tokuryu_individual_cases', title: 'トクリュウ 個別事案 全 12 ステップ', desc: 'ルフィ事件全過程 + 連続強盗+宝石店襲撃',
        steps: [
          { slug: 'komae_robbery_2023', banner: 'トクリュウ 個別事案 — 2023年から' },
          { slug: 'kanagawa_yokohama_robbery' },
          { slug: 'philippines_luffy_base' },
          { slug: 'luffy_court_proceedings' },
          { slug: 'luffy_satsumitsu_court' },
          { slug: 'tokuryu_pawn_jewelry_route' },
          { slug: 'jr_route_robbery_2024' },
          { slug: 'tokuryu_recruiter_takedown' },
          { slug: 'atm_uketakedashi_arrests' },
          { slug: 'tokuryu_crypto_laundering' },
          { slug: 'tokuryu_young_recruits' },
          { slug: 'school_predator_warning' },
        ]},
      { id: 'tokuryu_intl_full', title: 'トクリュウ 国際ネットワーク 全 9 ステップ', desc: 'フィリピン→カンボジア→ミャンマー→タイ→韓国',
        steps: [
          { slug: 'philippines_luffy_base', banner: 'トクリュウ 国際ネットワーク' },
          { slug: 'cambodia_compounds_link' },
          { slug: 'myanmar_compounds_link' },
          { slug: 'thailand_tokuryu_base' },
          { slug: 'tokuryu_kankoku_link' },
          { slug: 'intl_mekong_compounds_ref' },
          { slug: 'roman_sagi_centers' },
          { slug: 'special_fraud_callcenter' },
          { slug: 'npa_tokuryu_office' },
        ]},
      { id: 'tokuryu_japanese_victims', title: '日本人被害者 — トクリュウの加害-被害二重構造', desc: 'コンパウンド監禁→保護→若年実行役の被害',
        steps: [
          { slug: 'cambodia_compounds_link', banner: '日本人被害者の二重構造' },
          { slug: 'myanmar_compounds_link' },
          { slug: 'thailand_tokuryu_base' },
          { slug: 'tokuryu_young_recruits' },
          { slug: 'school_predator_warning' },
          { slug: 'bouhai_center_fukuoka' },
        ]},
      { id: 'media_books', title: 'ヤクザ報道書籍と研究', desc: '溝口敦・国正武重・Adelstein・Rankin・実話誌',
        steps: [
          { slug: 'magazine_tsukuru', banner: 'ヤクザ報道・研究の系譜' },
          { slug: 'jitsuwa_magazines' },
          { slug: 'mojiport_kitagata_book' },
          { slug: 'crows_kitakyu_setting' },
          { slug: 'hiroshima_korou_no_chi' },
        ]},
    ]
  },
];

function renderTourMenu() {
  const el = document.getElementById('tour-categories');
  el.innerHTML = '';
  for (const cat of TOUR_CATEGORIES) {
    const sec = document.createElement('div');
    sec.className = 'category';
    sec.innerHTML = `<div class="cat-head"><span class="cat-color" style="background:${cat.color};"></span>${escapeHtml(cat.name)}</div>`;
    const grid = document.createElement('div');
    grid.className = 'tours';
    for (const t of cat.tours) {
      const card = document.createElement('div');
      card.className = 'tour-card';
      card.style.borderLeft = `3px solid ${cat.color}`;
      card.innerHTML = `
        <div class="ttl">${escapeHtml(t.title)}</div>
        <div class="desc">${escapeHtml(t.desc)}</div>
        <div class="stops">▶ ${t.steps.length} ステップ</div>`;
      card.onclick = () => { startTour(t.steps); };
      grid.appendChild(card);
    }
    sec.appendChild(grid);
    el.appendChild(sec);
  }
}
renderTourMenu();

const tourMenuEl = document.getElementById('tour-menu');
function openTourMenu() { tourMenuEl.classList.add('show'); }
function closeTourMenu() { tourMenuEl.classList.remove('show'); }
document.getElementById('close-tour-menu').onclick = closeTourMenu;
document.getElementById('fab-tour')?.addEventListener('click', openTourMenu);

// Mobile FAB: help / POI / satellite — same handlers as right-side buttons
document.getElementById('fab-help')?.addEventListener('click', () => helpEl.classList.add('show'));
document.getElementById('fab-poi')?.addEventListener('click', () => {
  togglePoi.checked = !togglePoi.checked;
  togglePoi.dispatchEvent(new Event('change'));
  const btn = document.getElementById('fab-poi');
  btn.style.background = togglePoi.checked ? 'var(--accent)' : '#9aa6b2';
});
document.getElementById('fab-sat')?.addEventListener('click', () => {
  toggleSat.checked = !toggleSat.checked;
  toggleSat.dispatchEvent(new Event('change'));
  const btn = document.getElementById('fab-sat');
  btn.style.background = toggleSat.checked ? 'var(--accent)' : '#34495e';
});

tourPlayBtn.onclick = () => {
  tour.paused = !tour.paused;
  if (tour.paused) tourClearTimer();
  else { tour.timer = setTimeout(() => {
    if (tour.idx < tour.steps.length - 1) tourGoTo(tour.idx + 1);
    else tourHide();
  }, tour.stepDurationMs); }
  updateTourUI();
};
tourPrevBtn.onclick = () => { if (tour.idx > 0) tourGoTo(tour.idx - 1); };
tourNextBtn.onclick = () => { if (tour.idx < tour.steps.length - 1) tourGoTo(tour.idx + 1); else tourHide(); };
tourStopBtn.onclick = () => tourHide();

function runChronTour() {
  const acts = [
    { era: '戦後闇市', banner: '第1幕 ─ 戦後闇市の小倉(1947–)', slugs: ['kusano_ikka_origin_kokura', 'kudogumi_nakatsu_origin', 'uomachi_arcade', 'yawata_seitetsu_1901'] },
    { era: '高度成長', banner: '第2幕 ─ 神岳に本部が立つ(1980s)', slugs: ['yamaguchigumi_kyushu_entry', 'kudokai_hq_kandake', 'ogura_keisatsu'] },
    { era: '平成抗争', banner: '第3幕 ─ 市民への威迫(2000–2014)', slugs: ['heisei_shinten_chi', 'attack_1998_ashiya_fisheries', 'attack_2012_ex_officer', 'attack_2013_nurse', 'attack_2014_dentist', 'sakaimachi_quarter'] },
    { era: '頂上作戦', banner: '第4幕 ─ 頂上作戦と解体(2014–2021)', slugs: ['fukuoka_kenkei', 'kudokai_hq_kandake_signboard', 'kokura_district_court'] },
    { era: '解体後',   banner: '第5幕 ─ その後の街・トクリュウへ(2022–)', slugs: ['tanga_market', 'komae_robbery_2023', 'philippines_luffy_base'] },
  ];
  const steps = [];
  for (const act of acts) {
    act.slugs.forEach((slug, i) => {
      steps.push({ slug, banner: i === 0 ? act.banner : null });
    });
  }
  startTour(steps);
}

function runGossipTour() {
  const slugs = [
    'ogura_keisatsu', 'kudokai_hq_kandake_signboard', 'kusano_ikka_origin_kokura',
    'yamaguchigumi_kyushu_entry', 'kurume_dojinkai_hq', 'kokura_district_court',
    'tanaka_gumi_offshoot', 'philippines_luffy_base', 'kanto_rengo_ob_network',
  ];
  const steps = slugs.map((s, i) => ({ slug: s, banner: i === 0 ? '🟡 ゴシップ層 ─ 報道書籍と軼話で巡る' : null }));
  startTour(steps);
}

function runCases4Tour() {
  const slugs = ['attack_1998_ashiya_fisheries', 'attack_2012_ex_officer',
                 'attack_2013_nurse', 'attack_2014_dentist'];
  const steps = slugs.map((s, i) => ({ slug: s, banner: i === 0 ? '市民襲撃4事件 — 頂上作戦の起訴対象' : null }));
  startTour(steps);
}
</script>

</body>
</html>
"""


if __name__ == '__main__':
    main()
