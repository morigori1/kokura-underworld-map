"""Phase 8: collect a preview image URL (og:image) for each event source.

Individual-event news photos are copyright-protected, so we do NOT download them.
We fetch each source article's og:image (the social-card image, intended to be
linked) and store the URL. The dashboard shows it as a hot-linked preview
alongside a link to the article.

og:image fails for many sites (bot blocks, no tag, paywall); those events
simply show the article link with no preview. Many of our seeded sources have
NULL urls (canonical article not yet resolved); those are skipped.

Idempotent.
"""
from __future__ import annotations
import html as html_mod
import os, re, sqlite3, sys, time
import urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')
USER_AGENT = 'Mozilla/5.0 (Kokura-Map-OSINT/0.1)'


def fetch(url: str, timeout: int = 22) -> str:
    req = urllib.request.Request(
        url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,*/*'}
    )
    return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'ignore')


def og_image(htmltext: str) -> str:
    for pat in (
        r'<meta[^>]+(?:property|name)=["\']og:image(?::secure_url)?["\'][^>]*>',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']og:image["\']',
    ):
        m = re.search(pat, htmltext, re.I)
        if m:
            c = re.search(r'content=["\']([^"\']+)["\']', m.group(0))
            if c:
                return html_mod.unescape(c.group(1)).strip()
    return ''


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    urls = [
        r[0] for r in cur.execute(
            "SELECT DISTINCT url FROM source WHERE url LIKE 'http%' "
            "AND id IN (SELECT DISTINCT source_id FROM event WHERE source_id IS NOT NULL)"
        )
    ]
    print(f'[P8] {len(urls)} distinct source URLs to probe for og:image')

    ok = fail = 0
    for i, url in enumerate(urls, 1):
        img = ''
        try:
            img = og_image(fetch(url))
        except Exception as e:
            print(f'  [P8 ERR] {url[:60]} : {e}', file=sys.stderr)
        if img:
            cur.execute('UPDATE source SET og_image=? WHERE url=?', (img, url))
            ok += 1
            tag = 'OK '
        else:
            fail += 1
            tag = 'no '
        host = url.split('/')[2] if '://' in url else url
        print(f'  [{i:3d}/{len(urls)}] {tag} {host[:30]:30s} {img[:64]}')
        con.commit()
        time.sleep(0.7)

    print(f'[P8] done. preview image found for {ok} / {len(urls)} sources ({fail} without).')
    con.close()


if __name__ == '__main__':
    main()
