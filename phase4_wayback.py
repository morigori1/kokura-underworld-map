"""Phase 4: Esri Wayback historical satellite — build a per-site imagery timeline.

For each *narrative-relevant* site (HQ demolition, Tanga market fires) we fetch
the z15 center tile of every ~quarterly Wayback release, hash it, and keep the
releases where the imagery actually changed. That gives a time-machine track:

  - 工藤會本部跡(神岳1)  : 建物存在 → 解体 → 更地  (2014 → 2019 → 現在)
  - 旦過市場              : 火災前 → 火災後 → 仮設店舗 → 再整備

We deliberately skip chome-centroid attack sites where Wayback would only show
unchanged residential blocks (and where focusing satellite attention on a
victim's neighborhood would be undesirable).

Idempotent. Run: python phase4_wayback.py
"""
from __future__ import annotations
import datetime, hashlib, json, math, os, sqlite3, sys, time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')

CONFIG_URL = 'https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json'
USER_AGENT = 'Kokura-Map-OSINT/0.1'
TILE_Z = 17           # tighter zoom — block-scale change detection
MIN_GAP_DAYS = 90     # sample one Wayback release per ~quarter; enough to see HQ demolition / market fire

# Only these sites get Wayback frames. The narrative value comes from visible
# physical change (demolition, fire); chome-centroid attack sites are skipped.
WAYBACK_SITES = ('kudokai_hq_kandake', 'tanga_market')


def deg2tile(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 1 << z
    x = int((lon + 180) / 360 * n)
    y = int(
        (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi)
        / 2 * n
    )
    return x, y


def http(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout).read()


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute('DELETE FROM imagery_release')

    print('[WB] fetching wayback config ...')
    cfg = json.loads(http(CONFIG_URL, timeout=40))
    rels_all = sorted(
        ((int(k), v['itemTitle'][-11:-1], v['itemURL']) for k, v in cfg.items()),
        key=lambda r: r[1],
    )
    curated = []
    last_dt = None
    for num, date, tmpl in rels_all:
        try:
            dt = datetime.date.fromisoformat(date)
        except ValueError:
            continue
        if last_dt is None or (dt - last_dt).days >= MIN_GAP_DAYS:
            curated.append((num, date, tmpl))
            last_dt = dt
    print(f'[WB] {len(rels_all)} releases -> {len(curated)} curated, '
          f'{curated[0][1]} .. {curated[-1][1]}')

    grand_distinct = 0
    for slug in WAYBACK_SITES:
        row = cur.execute(
            'SELECT id, label, rep_lat, rep_lon FROM site WHERE slug=?', (slug,)
        ).fetchone()
        if not row or row[2] is None:
            print(f'  [WB SKIP] {slug}: no coords')
            continue
        site_id, label, lat, lon = row
        tx, ty = deg2tile(lat, lon, TILE_Z)
        last_hash = None
        distinct = 0
        for num, date, tmpl in curated:
            url = (tmpl.replace('{level}', str(TILE_Z))
                       .replace('{row}', str(ty))
                       .replace('{col}', str(tx)))
            try:
                body = http(url, timeout=20)
            except Exception as e:
                print(f'  [WB ERR] {label[:24]} {date}: {e}', file=sys.stderr)
                time.sleep(0.5)
                continue
            sha = hashlib.sha256(body).hexdigest()
            is_distinct = 1 if sha != last_hash else 0
            if is_distinct:
                distinct += 1
                last_hash = sha
            cur.execute(
                'INSERT INTO imagery_release(site_id, release_num, release_date, '
                ' tile_z, tile_x, tile_y, tile_url, tile_sha256, is_distinct) '
                ' VALUES (?,?,?,?,?,?,?,?,?)',
                (site_id, num, date, TILE_Z, tx, ty, tmpl, sha, is_distinct),
            )
            time.sleep(0.05)
        con.commit()
        grand_distinct += distinct
        print(f'  [WB] {label[:34]:34s}: {len(curated):3d} releases -> {distinct:2d} distinct frames')

    print(f'[WB] done. {grand_distinct} distinct frames across {len(WAYBACK_SITES)} sites.')
    con.close()


if __name__ == '__main__':
    main()
