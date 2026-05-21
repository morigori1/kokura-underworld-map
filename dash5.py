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
    '県警側':       '#2980b9',
    '司法側':       '#16a085',
    '市民側':       '#27ae60',
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
                 '山口組系', '道仁会系', '県警側', '司法側', '市民側']

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

    /* Side panel becomes a slide-up drawer — fully hidden by default */
    #side {
      position:fixed; top:auto; left:0; right:0; bottom:0; width:100%;
      max-height:70vh; height:70vh;
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

    /* Detail panel: bottom sheet (65vh) — map stays visible at top */
    #detail {
      position:fixed; top:auto; left:0; right:0; bottom:0;
      width:100%; max-width:none;
      height:65vh; max-height:65vh;
      border-left:none; border-top:2px solid var(--accent);
      border-radius:14px 14px 0 0;
      padding:8px 16px 18px;
      transform:translateY(100%);
      transition:transform 0.32s ease;
      box-shadow:0 -6px 20px rgba(0,0,0,0.5);
    }
    #detail.open { transform:translateY(0); }
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

    /* Timeline: compact 56px by default — date+title only. Tap expands. */
    #timeline { left:0; height:56px; transition:height 0.25s ease; }
    #timeline.expanded { height:140px; }
    #timeline-scroll { height:36px; padding:4px 8px; transition:height 0.25s ease; }
    #timeline.expanded #timeline-scroll { height:120px; padding:8px 10px; }
    .evt { width:160px; padding:4px 8px; font-size:11px; }
    #timeline.expanded .evt { width:200px; padding:6px 8px; font-size:12px; }
    .evt .sm { display:none; }
    #timeline.expanded .evt .sm { display:-webkit-box; }
    .evt .badges { display:none; }
    #timeline.expanded .evt .badges { display:block; }
    #era-ribbon { height:18px; font-size:9px; }
    #timeline-expand-tab {
      position:absolute; top:-22px; right:10px;
      background:var(--accent); color:#fff;
      padding:3px 12px; border-radius:6px 6px 0 0;
      font-size:11px; font-weight:600; cursor:pointer;
    }

    /* Legend hidden on mobile */
    #legend { display:none; }

    /* Right-side floating controls stack — minimal on mobile */
    #layers {
      top:auto; bottom:72px; right:8px;
      padding:6px 10px; font-size:11px;
      background:var(--panel); border:1px solid var(--line);
    }
    #layers label { margin:2px 0; }
    #help-btn {
      top:auto; bottom:148px; right:8px;
      width:36px; height:36px; font-size:14px;
    }
    /* Mobile FAB stack — left side: filter / menu */
    #mobile-fab-stack {
      position:fixed; left:8px; bottom:72px; z-index:1110;
      display:flex; flex-direction:column; gap:8px;
    }
    #mobile-fab-stack button {
      width:42px; height:42px; border-radius:50%;
      border:none; font-size:18px; font-weight:700; cursor:pointer;
      box-shadow:0 2px 8px rgba(0,0,0,0.5);
      display:flex; align-items:center; justify-content:center;
    }
    #fab-filter { background:var(--accent2); color:#000; }
    #fab-menu { background:var(--accent3); color:#fff; }

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
    <div class="way" data-way="map-free">
      <div class="num">▶ 5</div>
      <div class="ttl">自由に地図を開く</div>
      <div class="desc">89拠点ピンを自由探索。色分け切替・時代/派閥/出典フィルタで読み方を変える。</div>
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
  <button id="fab-filter" title="絞り込み・色分け">🔍</button>
  <button id="fab-menu" title="目次・系譜・人物">☰</button>
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
<div id="tour-banner"></div>

<div id="map"></div>

<div id="timeline">
  <div id="timeline-expand-tab">▲ 詳しく</div>
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
      // On mobile, detail covers bottom 65vh — shift map so marker is in
      // the visible upper ~35vh band (i.e. center the marker about 1/5
      // down from the top of the *full* viewport, not in the middle).
      const targetZoom = Math.max(map.getZoom(), 16);
      const targetPoint = map.project([s.lat, s.lon], targetZoom);
      const vh = window.innerHeight;
      // Shift down: we want the marker to appear ~vh*0.17 from the top
      // (centered in the visible 35vh top band). Default centers it at vh*0.5.
      // So offset Y by (vh*0.5 - vh*0.17) = vh*0.33 pixels downward in
      // screen-space, which moves the *view* by the same in projected coords.
      const adjusted = L.point(targetPoint.x, targetPoint.y + vh * 0.33);
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
function runCases4Tour() {
  const slugs = ['attack_1998_ashiya_fisheries', 'attack_2012_ex_officer',
                 'attack_2013_nurse', 'attack_2014_dentist'];
  showBanner('市民襲撃4事件 — 頂上作戦の起訴対象', 3000);
  let i = 0;
  function next() {
    if (i >= slugs.length) return;
    const rec = siteIndex[slugs[i++]];
    if (rec) {
      map.flyTo([rec.site.lat, rec.site.lon], 17, { duration: 1.5 });
      setTimeout(() => openDetail(rec.site.slug), 1600);
    }
    setTimeout(next, 7000);
  }
  next();
}

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

// ===== Timeline expand on mobile =====
const timelineEl = document.getElementById('timeline');
document.getElementById('timeline-expand-tab')?.addEventListener('click', () => {
  timelineEl.classList.toggle('expanded');
  const tab = document.getElementById('timeline-expand-tab');
  tab.textContent = timelineEl.classList.contains('expanded') ? '▼ 閉じる' : '▲ 詳しく';
});

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

function runChronTour() {
  const acts = [
    { era: '戦後闇市', banner: '第1幕 ─ 戦後闇市の小倉(1947–)', slugs: ['kusano_ikka_origin_kokura', 'kudogumi_nakatsu_origin', 'uomachi_arcade'] },
    { era: '高度成長', banner: '第2幕 ─ 神岳に本部が立つ(1980s)', slugs: ['yamaguchigumi_kyushu_entry', 'kudokai_hq_kandake', 'ogura_keisatsu'] },
    { era: '平成抗争', banner: '第3幕 ─ 市民への威迫(2000–2014)', slugs: ['heisei_shinten_chi', 'attack_1998_ashiya_fisheries', 'attack_2012_ex_officer', 'attack_2013_nurse', 'attack_2014_dentist', 'sakaimachi_quarter'] },
    { era: '頂上作戦', banner: '第4幕 ─ 頂上作戦と解体(2014–2021)', slugs: ['fukuoka_kenkei', 'kudokai_hq_kandake_signboard', 'kokura_district_court'] },
    { era: '解体後',   banner: '第5幕 ─ その後の街(2022–)', slugs: ['tanga_market', 'sakaimachi_quarter'] },
  ];
  let ai = 0, si = 0;
  function next() {
    if (ai >= acts.length) return;
    const act = acts[ai];
    if (si === 0) showBanner(act.banner, 3000);
    const slug = act.slugs[si];
    const rec = siteIndex[slug];
    if (rec) {
      map.flyTo([rec.site.lat, rec.site.lon], 17, { duration: 1.6 });
      setTimeout(() => openDetail(slug), 1700);
    }
    si++;
    if (si >= act.slugs.length) { ai++; si = 0; setTimeout(next, 5500); }
    else setTimeout(next, 6500);
  }
  next();
}

function runGossipTour() {
  const slugs = [
    'ogura_keisatsu', 'kudokai_hq_kandake_signboard', 'kusano_ikka_origin_kokura',
    'yamaguchigumi_kyushu_entry', 'kurume_dojinkai_hq', 'kokura_district_court',
    'tanaka_gumi_offshoot',
  ];
  showBanner('🟡 ゴシップ層 ─ 報道書籍と軼話で巡る', 3000);
  let i = 0;
  function next() {
    if (i >= slugs.length) return;
    const rec = siteIndex[slugs[i++]];
    if (rec) {
      map.flyTo([rec.site.lat, rec.site.lon], 17, { duration: 1.5 });
      setTimeout(() => openDetail(rec.site.slug), 1600);
    }
    setTimeout(next, 7000);
  }
  next();
}
</script>

</body>
</html>
"""


if __name__ == '__main__':
    main()
