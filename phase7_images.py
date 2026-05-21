"""Phase 7: collect freely-licensed location images from Wikimedia Commons.

For each site that benefits from a photo (the major landmarks; not the
chome-centroid attack sites — we deliberately do not download photos of victims'
neighborhoods), we search Commons by Japanese keyword, pick the first file
result, download a 1200px thumbnail, and record full attribution.

Idempotent: re-running clears image_resource and re-downloads.
"""
from __future__ import annotations
import json, os, re, sqlite3, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')
IMG_DIR = os.path.join(HERE, 'images')
os.makedirs(IMG_DIR, exist_ok=True)

USER_AGENT = 'Kokura-Map-OSINT/0.1 (educational visualization)'

# (site_slug, commons search keyword, fallback search keyword, caption)
QUERIES = [
    ('kokura_station',     '小倉駅',              'Kokura Station',
     '小倉駅 — 北九州の中心ターミナル'),
    ('tanga_market',       '旦過市場',            'Tanga Market',
     '旦過市場 — 戦後闇市起源の小路(2022年の二度の大火を経て再整備中)'),
    ('uomachi_arcade',     '魚町銀天街',          'Uomachi Ginten-gai',
     '魚町銀天街 — 日本初のアーケード商店街(1951)'),
    ('sakaimachi_quarter', '小倉北区 堺町',       'Sakaimachi Kokura',
     '小倉北区 堺町 — 九州有数の歓楽街'),
    ('kudokai_hq_kandake', '北九州市役所',        'Kitakyushu City Hall',
     '神岳1丁目周辺(本部跡の徒歩圏)— 北九州市役所など行政中枢が並ぶ'),
]


def http(url: str, timeout: int = 40) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout).read()


def http_retry(url: str, timeout: int = 60, tries: int = 5) -> bytes:
    for attempt in range(tries):
        try:
            return http(url, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:
                wait = 6 * (attempt + 1)
                print(f'    (429 — waiting {wait}s)', file=sys.stderr)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError('unreachable')


def commons_search_file(keyword: str) -> str | None:
    """Search Commons file namespace by keyword. Returns the first File: title or None."""
    params = {
        'action': 'query', 'format': 'json',
        'list': 'search', 'srsearch': keyword,
        'srnamespace': '6', 'srlimit': '5',
    }
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
    try:
        data = json.loads(http(url, timeout=30))
    except Exception as e:
        print(f'  [P7 search ERR] {keyword}: {e}', file=sys.stderr)
        return None
    hits = data.get('query', {}).get('search', [])
    for h in hits:
        title = h.get('title', '')
        # prefer photos: jpg/jpeg/png; skip SVG icons
        low = title.lower()
        if any(low.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.webp')):
            return title
    return hits[0]['title'] if hits else None


def commons_imageinfo(title: str) -> tuple[str, str, str, str]:
    """Return (thumb_url, license_short, author_text, description_url)."""
    params = {
        'action': 'query', 'format': 'json', 'titles': title,
        'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiurlwidth': '1200',
    }
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
    data = json.loads(http(url, timeout=30))
    page = next(iter(data['query']['pages'].values()))
    ii = page['imageinfo'][0]
    meta = ii.get('extmetadata', {})
    lic = meta.get('LicenseShortName', {}).get('value', 'unknown')
    author_html = meta.get('Artist', {}).get('value', 'unknown')
    author = re.sub('<[^>]+>', '', author_html).strip()
    author = re.sub(r'\s+', ' ', author)
    return ii.get('thumburl') or ii['url'], lic, author, ii.get('descriptionurl', '')


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute('DELETE FROM image_resource')
    con.commit()
    s_ids = {row[0]: row[1] for row in cur.execute('SELECT slug, id FROM site')}

    added = 0
    for idx, (slug, kw, kw_fb, caption) in enumerate(QUERIES):
        sid = s_ids.get(slug)
        if sid is None:
            print(f'  [P7 SKIP] no site for {slug}')
            continue

        title = commons_search_file(kw) or commons_search_file(kw_fb)
        if not title:
            print(f'  [P7 SKIP] no Commons hits for {kw} / {kw_fb}')
            continue

        try:
            thumb_url, lic, author, desc_url = commons_imageinfo(title)
        except Exception as e:
            print(f'  [P7 ERR] imageinfo {title}: {e}', file=sys.stderr)
            continue

        fname = f'{slug}_{idx}.jpg'
        fpath = os.path.join(IMG_DIR, fname)
        try:
            body = http_retry(thumb_url, timeout=60)
            with open(fpath, 'wb') as f:
                f.write(body)
        except Exception as e:
            print(f'  [P7 ERR] download {title}: {e}', file=sys.stderr)
            continue
        time.sleep(2.5)

        credit = f'{author} / {lic} (Wikimedia Commons)'
        cur.execute(
            'INSERT INTO image_resource(site_id, local_path, title, caption, '
            ' credit, license, source_url) VALUES (?,?,?,?,?,?,?)',
            (sid, f'images/{fname}', title, caption, credit, lic, desc_url),
        )
        added += 1
        print(f'  [P7] {slug:25s} <- {fname} ({len(body)//1024} KB) | {lic} | {author[:40]}')

    con.commit()
    print(f'[P7] saved {added} images with attribution.')
    con.close()


if __name__ == '__main__':
    main()
