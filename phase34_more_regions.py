"""Phase 34: 北海道・東北・四国・北陸 未カバー地域の事件・lore 追加。

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('rg_hokkaido_yakuza', 'news', '北海道新聞 / 朝日新聞',
     '北海道ヤクザ情勢 関連報道', 'https://www.hokkaido-np.co.jp/', '2010-'),
    ('rg_susukino_bouhai', 'news', '北海道新聞 / 札幌市',
     'すすきの 暴排運動報道', 'https://www.hokkaido-np.co.jp/', '2010-'),
    ('rg_sendai_kokubun_history', 'news', '河北新報 / 朝日新聞',
     '仙台 国分町 戦後ヤクザ史', 'https://www.kahoku.news/', '1950s-'),
    ('rg_fukushima_renge', 'news', '朝日新聞 / 福島民報',
     '福島連合 関連報道', 'https://www.minpo.jp/', '1990s-'),
    ('rg_311_disaster_bouhai', 'official_release', '警察庁 / 福島県警',
     '東日本大震災 暴排運動 関連発表', 'https://www.npa.go.jp/', '2011-'),
    ('rg_311_yakuza_concern', 'news', '朝日新聞 / 河北新報',
     '震災復興とヤクザ系企業排除', 'https://www.asahi.com/', '2011-2014'),
    ('rg_takamatsu_marugame', 'news', '四国新聞 / 朝日新聞',
     '高松 丸亀町 暴排・再開発', 'https://www.shikoku-np.co.jp/', '2010-'),
    ('rg_matsuyama_bantencho', 'news', '愛媛新聞',
     '松山 大街道・銀天街 関連報道', 'https://www.ehime-np.co.jp/', '2010-'),
    ('rg_shikoku_yamaguchi', 'book', '報道書籍',
     '四国地場ヤクザと山口組系進出', None, '1980s-'),
    ('rg_niigata_furumachi', 'news', '新潟日報',
     '新潟 古町 戦後ヤクザ史', 'https://www.niigata-nippo.co.jp/', '1950s-'),
    ('rg_kanazawa_katamachi', 'news', '北國新聞',
     '金沢 香林坊・片町 関連報道', 'https://www.hokkoku.co.jp/', '2010-'),
    ('rg_chuetsu_quake', 'news', '新潟日報 / 朝日新聞',
     '新潟県中越地震 暴排運動報道', 'https://www.niigata-nippo.co.jp/', '2004-2007'),
    ('rg_hakodate_motomachi', 'book', '函館市史 / 報道書籍',
     '函館 戦後ヤクザ史', None, '1950s-'),
    ('rg_otaru_unga', 'book', '小樽市史',
     '小樽 港湾労働者街と戦後ヤクザ', None, '1950s-'),
]


EVENTS = [
    # ===== 北海道 =====
    ('sapporo_susukino', 'rg_susukino_bouhai',
     'lore', '1992-',
     'すすきの 暴排運動の段階的進展',
     '1992年の暴対法施行以降、すすきの歓楽街では暴排運動が段階的に進展。'
     '札幌市・北海道警察・商店街振興組合の連携で、'
     '暴排ステッカー普及・暴排相談窓口設置が進んだ。'
     'すすきの観光協会も組合員企業の反社チェックを継続的に行う。',
     None, None, None, '頂上作戦', '司法側', 3),

    ('sapporo_susukino', 'rg_hokkaido_yakuza',
     'lore', '1980s-',
     'すすきの — 山口組系の進出地',
     'すすきのは1980年代以降の山口組系列の北海道進出地として継続的に '
     '報道される。地場ヤクザ系統と山口組系の縄張りが交錯する複合エリア。',
     None, None, None, '高度成長', '山口組系', 3),

    ('hokkaido_keisatsu', 'rg_hokkaido_yakuza',
     'lore', '2010-',
     '北海道警察 — 広域対応',
     '北海道は面積最大の県警管轄で、広大な地域の組織犯罪情勢に対応。'
     '札幌・函館・小樽・釧路など主要都市の歓楽街に対する継続的な暴排取り組み。',
     None, None, None, '頂上作戦', '県警側', 2),

    ('hakodate_chinatown', 'rg_hakodate_motomachi',
     'lore', '1950s-',
     '函館 — 国際港町と組織犯罪文化',
     '函館は明治期からの国際港町として、'
     '神戸・横浜・長崎と並ぶ戦後ヤクザ史の港町コンテキストの一つ。'
     '元町・末広町の風景の中に戦後の物語が残る。',
     None, None, None, '戦後闇市', '司法側', 2),

    ('otaru_yakuza_history', 'rg_otaru_unga',
     'lore', '1950s-1970s',
     '小樽 — 港湾労働者街の戦後',
     '小樽運河沿いの色内エリアは戦後港湾労働者街。'
     '戦後闇市文化と港湾労働の交点として、北海道ヤクザ史の前史。'
     '現在は観光地化が進む。',
     None, None, None, '戦後闇市', '司法側', 2),

    # ===== 東北 =====
    ('sendai_kokubun', 'rg_sendai_kokubun_history',
     'lore', '1950s-',
     '国分町 — 東北最大の歓楽街の戦後',
     '仙台市青葉区 国分町は約2000店舗の東北最大の歓楽街。'
     '戦後から指定暴力団・地場組織の活動エリアとして発展。'
     '2011年東日本大震災後の復興期に暴排運動が大幅に強化された。',
     None, None, None, '高度成長', '司法側', 3),

    ('sendai_kokubun', 'rg_311_disaster_bouhai',
     'lore', '2011-2015',
     '震災後の国分町 — 暴排運動加速',
     '東日本大震災後、国分町では復興事業に絡む不当要求への警戒が高まり、'
     '宮城県警・地元組合の連携で暴排ステッカー普及・通報窓口整備が加速した。',
     None, None, None, '頂上作戦', '市民側', 3),

    ('koriyama_fukushima_renge', 'rg_fukushima_renge',
     'lore', '1990s-',
     '福島連合 — 東北唯一の指定暴力団系統',
     '福島連合は東北唯一の地場指定暴力団系統として継続。'
     '福島県郡山市を中心に活動。'
     '2011年福島第一原発事故・震災復興事業の関連で、'
     '警察庁・福島県警は専門対策チームを組織した。',
     None, None, None, '平成抗争', '司法側', 3),

    ('disaster_311_yakuza_response', 'rg_311_yakuza_concern',
     'attack', '2011-2014',
     '震災復興 — ヤクザ系企業排除',
     '東日本大震災後の復興事業(瓦礫処理・除染・公共工事)から '
     'ヤクザ系企業を排除する取り組みが大規模に行われた。'
     '警察庁・各県警の専門チームが事業者の反社チェックを継続。',
     None, None, None, '頂上作戦', '司法側', 4),

    ('disaster_311_yakuza_response', 'rg_311_disaster_bouhai',
     'lore', '2011-',
     '原発事故 — 除染とヤクザ',
     '福島第一原発事故後の除染事業に絡むヤクザ系企業の関与が懸念され、'
     '警察庁・福島県警が継続的に監視。'
     '労働者派遣・元請け体制の透明化が大きな課題となった。',
     None, None, None, '頂上作戦', '司法側', 3),

    # ===== 四国 =====
    ('takamatsu_marugame', 'rg_takamatsu_marugame',
     'lore', '2000s-',
     '丸亀町商店街 — 暴排・再開発の全国モデル',
     '高松市 丸亀町商店街(約1500m)は日本最古級のアーケード商店街。'
     '商店街振興組合主導の暴排運動・再開発(2007-)が全国モデルとして '
     '紹介された。'
     '組合員の経済的自立と暴排の両立を実現した成功例。',
     None, None, None, '頂上作戦', '市民側', 3),

    ('matsuyama_bantencho', 'rg_matsuyama_bantencho',
     'lore', '2010-',
     '松山 大街道・銀天街',
     '松山市の大街道・銀天街は四国最大級の商業地。'
     '四国地場の指定暴力団系列の活動エリアとして継続的に報道される。'
     '愛媛県警・松山市・商店街組合連携の暴排運動。',
     None, None, None, '頂上作戦', '司法側', 2),

    ('shikoku_yakuza_landscape', 'rg_shikoku_yamaguchi',
     'lore', '1980s-',
     '四国 — 山口組系の進出と地場の併存',
     '四国4県は1980年代以降の山口組系列の進出地として継続的に注目。'
     '地場連合体と山口組系の縄張りが交錯。'
     '各県警の継続的対応で2010年代以降は組織犯罪情勢が安定化傾向。',
     None, None, None, '高度成長', '山口組系', 3),

    ('kagawa_keisatsu', 'rg_takamatsu_marugame',
     'lore', '2010-',
     '四国管区警察局 — 4県の集約',
     '高松市の四国管区警察局は香川・徳島・愛媛・高知の4県の '
     '組織犯罪情勢の中央集約地。'
     '広域連携が必要な事案で機能する。',
     None, None, None, '頂上作戦', '県警側', 2),

    # ===== 北陸 =====
    ('niigata_furumachi', 'rg_niigata_furumachi',
     'lore', '1700s-',
     '古町 — 日本海側最大の歓楽街の戦後',
     '新潟市中央区 古町は江戸時代の港町文化から発展した '
     '日本海側最大の歓楽街。'
     '戦後から指定暴力団系列の活動エリアとして報道される。'
     '芸者文化と現代の歓楽街が共存する独特の風情。',
     None, None, None, '高度成長', '司法側', 3),

    ('niigata_chuetsu_jishin', 'rg_chuetsu_quake',
     'lore', '2004-2007',
     '中越地震・中越沖地震と暴排運動',
     '2004年新潟県中越地震・2007年中越沖地震を経て、'
     '新潟県内の災害復興と暴排運動が並走した経緯。'
     '災害便乗の不当業者への警戒が地域住民レベルで定着した。'
     '東日本大震災時(2011)の対応の素地となった。',
     None, None, None, '平成抗争', '市民側', 3),

    ('kanazawa_katamachi', 'rg_kanazawa_katamachi',
     'lore', '1950s-',
     '香林坊・片町 — 北陸最大の歓楽街',
     '金沢市の香林坊・片町は北陸最大級の歓楽街。'
     '伝統的茶屋街(東山・西山・主計町)と現代の歓楽街が共存。'
     '指定暴力団・山口組系列の進出地として継続的に注目される。',
     None, None, None, '高度成長', '司法側', 2),

    ('toyama_keisatsu_area', 'rg_hokkaido_yakuza',
     'lore', '2010-',
     '北陸三県警察連携',
     '富山・石川・福井の北陸三県警は組織犯罪情勢への合同対応を継続。'
     '日本海側の密輸ルート対応も重要任務。',
     None, None, None, '頂上作戦', '県警側', 2),
]


LORE = [
    (5000, 'sapporo_susukino', '1980s-',
     'すすきの — 「地下」と「観光」の二層',
     '札幌すすきのは観光客向けの表の歓楽街と、'
     '地元客向けの裏側の二層構造で発展してきた。'
     'インバウンド観光の急拡大で表側が国際化する一方、'
     '裏側は地場の組織犯罪情勢が継続する複合構造。',
     3, '高度成長', '司法側', 'rg_susukino_bouhai'),

    (5010, 'sendai_kokubun', '2011-',
     '震災後の国分町 — 「復興景気」と暴排',
     '東日本大震災後の国分町は「復興景気」で一時急速に活況。'
     '建設関係者・公共工事関係者の宿泊・飲食需要が急増した。'
     '同時にヤクザ系企業の介入懸念も高まり、'
     '宮城県警の暴排部隊が継続的に対応。',
     4, '頂上作戦', '市民側', 'rg_311_yakuza_concern'),

    (5020, 'disaster_311_yakuza_response', '2011-2014',
     '除染事業 — 透明化の挑戦',
     '福島第一原発事故後の除染事業は、巨額の公的資金が投入される事業。'
     'ヤクザ系企業・労働者派遣業者の中間搾取が懸念され、'
     '元請け企業の透明化・労働者の身元確認が大きな課題に。'
     '警察庁・福島県警の専門チームが継続的に監視。',
     4, '頂上作戦', '司法側', 'rg_311_yakuza_concern'),

    (5030, 'takamatsu_marugame', '2007-',
     '丸亀町再開発 — 暴排と経済自立の両立',
     '高松丸亀町商店街は商店街振興組合の独自再開発(2007-)で全国に注目された。'
     '暴排運動と組合員の経済的自立を両立させた成功例として、'
     '他県の商店街にもモデルとして紹介される。',
     3, '頂上作戦', '市民側', 'rg_takamatsu_marugame'),

    (5040, 'shikoku_yakuza_landscape', '1980s-',
     '四国 — 山口組進出 vs 地場連合',
     '四国4県は1980年代の山口組進出で地場連合体との緊張が高まった。'
     '工藤會のような明確な単一支配ではなく、'
     '各県で独自の組織犯罪情勢が並存する複合的状況。',
     3, '高度成長', '山口組系', 'rg_shikoku_yamaguchi'),

    (5050, 'niigata_furumachi', '1700s-',
     '古町 — 芸者文化と組織犯罪の戦後',
     '新潟古町は江戸時代の北前船寄港地。'
     '芸者文化が継承される独特の歓楽街で、'
     '戦後の組織犯罪も独自の経路で発展した。',
     3, '戦後闇市', '司法側', 'rg_niigata_furumachi'),

    (5060, 'koriyama_fukushima_renge', '2011-',
     '原発事故後の福島連合 — 復興と暴排',
     '福島第一原発事故後、福島連合の動向は復興事業との関連で警察庁の '
     '継続的監視対象。'
     '震災・原発事故・暴排運動が同時並行で進行した東北の特殊な状況。',
     4, '頂上作戦', '司法側', 'rg_fukushima_renge'),
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
    print(f'phase34_more_regions: +{ev_inserted} events, +{lr_inserted} lore')
    if missing: print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
