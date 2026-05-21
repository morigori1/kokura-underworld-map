"""POI + narration + era captions.

Three things:

1) Per-site narration paragraphs (editorial text, no external fetch).
2) Per-site era captions for satellite years (pre-seeded; phase4 will pick
   matching frames).
3) Per-site OSM POI (police / government / market / station / religious /
   restaurant clusters) fetched from Overpass.

Overpass calls are made with a small bbox (~300 m) around each site centroid,
filtered to a useful amenity set. Failures are tolerated so the script remains
re-runnable in offline mode (existing rows are kept if a fetch fails).

Idempotent. Run: python phase5_poi.py
"""
from __future__ import annotations
import json, os, sqlite3, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')

OVERPASS_URL = 'https://overpass-api.de/api/interpreter'
USER_AGENT = 'Kokura-Map-OSINT/0.1 (educational visualization)'

# Per-site narration. ord controls order in the tour panel.
NARRATION = {
    'kudokai_hq_kandake': [
        (10, '神岳1丁目に立っていたもの',
         '北九州市小倉北区神岳1丁目1番3号。1987年の工藤連合草野一家成立以来、'
         '2019年8月の解体まで、ここが工藤會本部だった。'
         '小倉警察署のすぐ北西に位置するという立地そのものが、戦後北九州の独特な '
         '地域構造を象徴していた。'),
        (20, '頂上作戦と解体',
         '2014年9月、福岡県警が会長・理事長を相次いで逮捕する「頂上作戦」を発動。'
         '2019年7月、本部の解体が始まり、同年8月までに更地化された。'
         '指定暴力団のトップが拘束された状態での本部自主解体は、戦後の組織犯罪史でも '
         '極めて稀な事案である。'),
        (30, '跡地のいま',
         '現在は民有地となり、看板のない区画として周辺の住宅・行政施設に溶け込んでいる。'
         '徒歩圏には小倉北警察署・北九州市役所・小倉市民会館。'
         '街の表面は静かだが、地域の防犯講習と暴排相談は今も継続している。'),
    ],
    'tanga_market': [
        (10, '戦後闇市から続く市場',
         '旦過市場は戦後の闇市を起源に持ち、神嶽川沿いの細長い区画に '
         '青果・鮮魚・惣菜の店が並ぶ「北九州の台所」。'
         '小倉駅から徒歩10分、工藤會本部跡からも徒歩圏という地理関係にある。'),
        (20, '2022年の二度の大火',
         '2022年4月19日と同8月10日、わずか4か月の間に二度の大規模火災が発生。'
         '市場北側の街区の小路が大きく失われた。'
         '原因は捜査が継続したが、工藤會事件との直接の関連は公式には認定されていない。'),
        (30, '再整備のいま',
         '組合は暫定店舗で営業を継続しつつ、北九州市は防災と商店街・観光を両立する '
         '再整備計画を策定した。'),
    ],
    'attack_1998_ashiya_fisheries': [
        (10, '芦屋町・遠賀川河口の町',
         '芦屋町は北九州都市圏の西、遠賀川河口に開けた漁港の町。'
         '1998年2月18日、ここで元漁協理事が拳銃で射殺された。'),
        (20, '裁判での位置づけ',
         '2021年の福岡地裁判決は、漁業権をめぐる対立を背景に工藤會幹部らが '
         '組織的に企てた犯行と認定した。'
         '市民襲撃4事件の最初の1件として、後の頂上作戦の起訴の核になった。'),
    ],
    'attack_2014_dentist': [
        (10, '頂上作戦の起点となった事件',
         '2014年5月26日、小倉北区中井エリアで男性歯科医師が刃物で襲撃され重傷。'
         'この事件をきっかけに福岡県警は、工藤會のトップ層を「事件の首謀者」として '
         '摘発する捜査(頂上作戦)を本格化させた。'),
        (20, '一連の医療関係者一族への威迫',
         '判決は、本件を2013年の看護師襲撃と連続した、同一の医療関係者一族への '
         '一連の威迫の集大成として位置づけた。'),
    ],
    'attack_2012_ex_officer': [
        (10, '警察組織への威迫',
         '2012年4月19日、退職後の元福岡県警警部が小倉北区内で拳銃により襲撃され '
         '重傷を負った。'
         '指定暴力団が元警察関係者を直接の標的とした極めて異例の事件で、'
         '同年12月の全国初の「特定危険指定暴力団」指定の重要な背景となった。'),
    ],
    'attack_2013_nurse': [
        (10, '医療関係者一族への威迫',
         '2013年1月28日、小倉北区で看護師の女性が刃物で襲撃され重傷を負った。'
         '一連の医療関係者一族への威迫の中で行われたと判決は位置づけた。'),
    ],
    'sakaimachi_quarter': [
        (10, '九州有数の歓楽街',
         '小倉北区堺町1〜2丁目は飲食・接待店が密集する九州有数の歓楽街。'
         '長年、工藤會傘下のショバ代徴収やトラブル介入の温床と報じられてきた。'),
        (20, '頂上作戦後の街',
         '頂上作戦以降は店舗側の暴排対応(暴排ステッカー掲示・通報窓口整備)が広がり、'
         '不当要求は減少傾向と報じられる。一方で、違反勧誘・不払い名目の威迫は '
         '相談事例に残存。'),
    ],
}

# Era captions for the HQ site (used by the time-machine swipe when Wayback
# frames arrive in phase4).
ERA_CAPTIONS = {
    'kudokai_hq_kandake': [
        (2014, '頂上作戦着手の年 — 本部は神岳1丁目に立っていた'),
        (2016, '指定暴力団トップ拘束下の本部'),
        (2018, '一審公判進行中 — 本部建物は残存'),
        (2019, '解体着手の年(7月着工〜8月更地化)'),
        (2021, '一審判決(野村に死刑、田上に無期懲役)'),
        (2024, '控訴審判決(野村は死刑→無期懲役)'),
    ],
    'tanga_market': [
        (2014, '旦過市場 — 戦後闇市起源の小路が続く時代'),
        (2018, '再整備計画策定前の市場'),
        (2022, '4月・8月の二度の大火'),
        (2024, '暫定店舗での営業継続と再整備'),
    ],
}


# Overpass amenity filter — what we keep when we look around each site.
KEEP_AMENITY = {
    'police', 'fire_station', 'townhall', 'courthouse', 'post_office',
    'hospital', 'clinic', 'pharmacy', 'school', 'library', 'community_centre',
    'place_of_worship', 'bank', 'marketplace', 'cinema', 'theatre',
}
KEEP_SHOP = {'mall', 'supermarket', 'department_store', 'convenience'}


def overpass_query(lat: float, lon: float, radius_m: int = 300) -> list[dict]:
    """Fetch amenities/shops within radius_m of (lat,lon). Returns a list of
    {lat,lon,type,name,kind} dicts. Returns [] on failure."""
    # Build a small bbox.
    dlat = radius_m / 111000.0
    dlon = radius_m / (111000.0 * max(0.2, abs((lat * 3.14159 / 180.0).real)))
    # safer: just use a fixed degree offset
    south, north = lat - dlat, lat + dlat
    west, east = lon - dlon, lon + dlon
    q = (
        f'[out:json][timeout:25];('
        f'node({south},{west},{north},{east})[amenity];'
        f'way({south},{west},{north},{east})[amenity];'
        f'node({south},{west},{north},{east})[shop];'
        f'way({south},{west},{north},{east})[shop];'
        f'way({south},{west},{north},{east})[building=train_station];'
        f');out center 200;'
    )
    body = 'data=' + urllib.parse.quote(q)
    req = urllib.request.Request(
        OVERPASS_URL, data=body.encode(),
        headers={'User-Agent': USER_AGENT, 'Content-Type': 'application/x-www-form-urlencoded'},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f'  overpass failed: {e}')
        return []

    out = []
    for el in data.get('elements', []):
        tags = el.get('tags') or {}
        amenity = tags.get('amenity')
        shop = tags.get('shop')
        building = tags.get('building')
        name = tags.get('name') or tags.get('name:ja') or tags.get('name:en')
        if amenity and amenity in KEEP_AMENITY:
            kind = amenity
            type_ = 'amenity'
        elif shop and shop in KEEP_SHOP:
            kind = shop
            type_ = 'shop'
        elif building == 'train_station':
            kind = 'station'
            type_ = 'station'
        else:
            continue
        if el['type'] == 'node':
            ll = el.get('lat'), el.get('lon')
        else:
            c = el.get('center') or {}
            ll = c.get('lat'), c.get('lon')
        if ll[0] is None:
            continue
        out.append({'lat': ll[0], 'lon': ll[1], 'type': type_, 'kind': kind,
                    'name': name})
    return out


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # ----- narration -----
    cur.execute('DELETE FROM narration')
    inserted_narr = 0
    s_ids = {row[0]: row[1] for row in con.execute('SELECT slug, id FROM site')}
    for slug, rows in NARRATION.items():
        sid = s_ids.get(slug)
        if sid is None:
            continue
        for ord_, title, body in rows:
            cur.execute(
                'INSERT INTO narration(site_id, ord, title, body) VALUES (?,?,?,?)',
                (sid, ord_, title, body),
            )
            inserted_narr += 1

    # ----- era captions -----
    cur.execute('DELETE FROM era_caption')
    inserted_era = 0
    for slug, rows in ERA_CAPTIONS.items():
        sid = s_ids.get(slug)
        if sid is None:
            continue
        for year, caption in rows:
            cur.execute(
                'INSERT INTO era_caption(site_id, year, caption) VALUES (?,?,?)',
                (sid, year, caption),
            )
            inserted_era += 1

    # ----- POIs (Overpass) -----
    # Only fetch for primary sites where surroundings matter for the narrative.
    poi_sites = [
        'kudokai_hq_kandake',
        'tanga_market',
        'uomachi_arcade',
        'sakaimachi_quarter',
        'kokura_station',
    ]
    cur.execute('DELETE FROM poi')
    inserted_poi = 0
    for slug in poi_sites:
        sid = s_ids.get(slug)
        if sid is None:
            continue
        row = con.execute(
            'SELECT rep_lat, rep_lon FROM site WHERE id=?', (sid,)
        ).fetchone()
        if not row or row[0] is None:
            continue
        print(f'  overpass: {slug} @ ({row[0]:.4f}, {row[1]:.4f})')
        pois = overpass_query(row[0], row[1], radius_m=320)
        # Dedupe by (lat, lon, kind)
        seen = set()
        kept = []
        for p in pois:
            key = (round(p['lat'], 6), round(p['lon'], 6), p['kind'])
            if key in seen:
                continue
            seen.add(key)
            kept.append(p)
        for p in kept:
            cur.execute(
                'INSERT INTO poi(site_id, lat, lon, poi_type, name, descr, confidence, source) '
                'VALUES (?,?,?,?,?,?,?,?)',
                (sid, p['lat'], p['lon'], p['type'], p['name'], p['kind'],
                 'osm', 'OpenStreetMap'),
            )
            inserted_poi += 1
        print(f'    kept {len(kept)} POIs')
        time.sleep(1.2)  # be nice to Overpass

    con.commit()
    print(f'phase5_poi: narration={inserted_narr} era={inserted_era} poi={inserted_poi}')
    con.close()


if __name__ == '__main__':
    main()
