"""Render a single-file HTML dashboard from project.db.

The HTML embeds the entire dataset as a JSON payload in a <script> tag, then
Leaflet + vanilla JS handles all interaction client-side. The output file
opens directly in any browser without a web server.

This is a MINIMAL starter — extend with timeline, tour, filters as needed.
See the parent project's dash5.py for the full-featured version.

Run: python dash.py  →  produces index.html
"""
from __future__ import annotations
import json
import os
import sqlite3
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'project.db')
OUT = os.path.join(HERE, 'index.html')


def fetch_dicts(cur, sql, *args):
    cur.execute(sql, args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def build_payload():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    sites_rows = fetch_dicts(cur, """
        SELECT s.id, s.slug, s.label, s.rep_lat AS lat, s.rep_lon AS lon,
               s.kind, s.notes, s.era_tag, s.faction_tag,
               p.name_canonical AS place
        FROM site s LEFT JOIN place p ON s.place_id = p.id
        ORDER BY s.id
    """)
    sites = []
    for s in sites_rows:
        sid = s['id']
        s['narration'] = fetch_dicts(cur,
            'SELECT title, body, created_by FROM narration WHERE site_id=? ORDER BY ord',
            sid)
        s['events'] = fetch_dicts(cur,
            'SELECT kind, happened_on AS date, title, summary, severity FROM event '
            'WHERE site_id=? ORDER BY happened_on', sid)
        sites.append(s)
    con.close()
    return {'sites': sites}


HTML_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>OSINT Starter Dashboard</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="vendor/leaflet/leaflet.css">
<style>
  body, html { margin:0; padding:0; height:100%; font-family:-apple-system, sans-serif; }
  #map { position:absolute; inset:0; }
  #detail {
    position:fixed; top:0; right:0; bottom:0; width:380px;
    background:#fff; border-left:1px solid #ccc; overflow:auto; padding:18px;
    transform:translateX(100%); transition:transform 0.32s ease;
    box-shadow:-4px 0 12px rgba(0,0,0,0.15);
  }
  #detail.open { transform:translateX(0); }
  #detail h2 { margin:0 0 8px; }
  #detail .close { float:right; cursor:pointer; font-size:18px; }
  #detail .narration p { line-height:1.6; }
  #detail .events { margin-top:12px; }
  #detail .event { padding:6px 8px; margin:4px 0; background:#f5f5f5; border-left:3px solid #d9534f; }
  #detail .meta { color:#666; font-size:12px; }
  .provenance-llm { color:#999; font-size:10px; font-style:italic; }
</style>
</head>
<body>
<div id="map"></div>
<div id="detail">
  <span class="close" onclick="closeDetail()">✕</span>
  <div id="detail-body"></div>
</div>

<script src="vendor/leaflet/leaflet.js"></script>
<script>
const DATA = __PAYLOAD__;

const map = L.map('map').setView([35.6762, 139.6503], 12);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap'
}).addTo(map);

for (const s of DATA.sites) {
  if (!s.lat || !s.lon) continue;
  const marker = L.circleMarker([s.lat, s.lon], {
    radius:8, fillColor:'#d9534f', color:'#fff', weight:2, fillOpacity:0.9
  }).addTo(map);
  marker.bindPopup(`<b>${s.label}</b>`);
  marker.on('click', () => openDetail(s));
}

function openDetail(s) {
  const body = document.getElementById('detail-body');
  const parts = [];
  parts.push(`<h2>${escapeHtml(s.label)}</h2>`);
  parts.push(`<div class="meta">${escapeHtml(s.place || '')} · ${escapeHtml(s.kind || '')}</div>`);
  if (s.notes) parts.push(`<p>${escapeHtml(s.notes)}</p>`);
  if (s.narration && s.narration.length) {
    parts.push('<h3>解説</h3><div class="narration">');
    for (const n of s.narration) {
      parts.push(`<h4>${escapeHtml(n.title)}</h4>`);
      parts.push(`<p>${escapeHtml(n.body)}</p>`);
      if (n.created_by && n.created_by.startsWith('llm:')) {
        parts.push(`<div class="provenance-llm">⚠ AI 生成・要検証</div>`);
      }
    }
    parts.push('</div>');
  }
  if (s.events && s.events.length) {
    parts.push('<h3>事件</h3><div class="events">');
    for (const e of s.events) {
      parts.push(`<div class="event"><b>${escapeHtml(e.date)}</b> ${escapeHtml(e.title)}<br><span class="meta">${escapeHtml(e.summary)}</span></div>`);
    }
    parts.push('</div>');
  }
  body.innerHTML = parts.join('');
  document.getElementById('detail').classList.add('open');
}
function closeDetail() {
  document.getElementById('detail').classList.remove('open');
}
function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
</script>
</body>
</html>
"""


def main():
    payload = build_payload()
    html = HTML_TEMPLATE.replace('__PAYLOAD__', json.dumps(payload, ensure_ascii=False))
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Wrote {OUT}')
    print(f'  sites: {len(payload["sites"])}')
    print('  open in browser: file://' + OUT)


if __name__ == '__main__':
    main()
