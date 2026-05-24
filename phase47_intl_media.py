"""Phase 47: 海外拠点に各国の主要メディア・公的機関を追加。

国別の主要紙・テレビ・国家警察・関連機関・在外日本大使館をマッピング。

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


INTL_MEDIA_BY_COUNTRY = {
    # === Philippines (Luffy 事件) ===
    'PH': [
        ('newspaper', 'Philippine Daily Inquirer', 'https://www.inquirer.net/',
         'フィリピン主要英字日刊紙'),
        ('newspaper', 'Manila Bulletin', 'https://mb.com.ph/', None),
        ('newspaper', 'GMA News Online', 'https://www.gmanetwork.com/news/',
         'フィリピン主要メディア'),
        ('newspaper', 'Rappler', 'https://www.rappler.com/',
         '調査報道で著名'),
        ('tv', 'ABS-CBN News', 'https://news.abs-cbn.com/', None),
        ('pref_police', 'Philippine National Police (PNP)', 'https://www.pnp.gov.ph/',
         'フィリピン国家警察'),
        ('other', 'Bureau of Immigration (BI)', 'https://www.immigration.gov.ph/',
         '入管(ルフィ事件の Bicutan 収容施設管轄)'),
        ('city_gov', '在フィリピン日本国大使館',
         'https://www.ph.emb-japan.go.jp/itprtop_ja/index.html', None),
    ],

    # === Cambodia ===
    'KH': [
        ('newspaper', 'Phnom Penh Post', 'https://www.phnompenhpost.com/',
         'カンボジア主要英字紙'),
        ('newspaper', 'Khmer Times', 'https://www.khmertimeskh.com/', None),
        ('newspaper', 'VOD English', 'https://vodenglish.news/',
         '独立調査報道'),
        ('pref_police', 'Cambodian National Police',
         'https://police.gov.kh/', None),
        ('city_gov', '在カンボジア日本国大使館',
         'https://www.kh.emb-japan.go.jp/itpr_ja/00_000023.html', None),
        ('npo', 'Global Anti-Scam Org (GASO)', 'https://www.globalantiscam.org/',
         '詐欺コンパウンド被害者支援'),
    ],

    # === Myanmar ===
    'MM': [
        ('newspaper', 'Frontier Myanmar', 'https://www.frontiermyanmar.net/en/',
         'ミャンマー独立英字紙'),
        ('newspaper', 'Myanmar Now', 'https://myanmar-now.org/en/',
         '独立報道'),
        ('newspaper', 'The Irrawaddy', 'https://www.irrawaddy.com/',
         'ミャンマー国境地帯・少数民族問題に強い'),
        ('city_gov', '在ミャンマー日本国大使館',
         'https://www.mm.emb-japan.go.jp/itpr_ja/00_000043.html', None),
        ('npo', 'Karen National Union (KNU)',
         'https://www.knuhq.org/',
         '国境地帯コンパウンド地域の少数民族組織'),
    ],

    # === Thailand ===
    'TH': [
        ('newspaper', 'Bangkok Post', 'https://www.bangkokpost.com/',
         'タイ主要英字日刊紙'),
        ('newspaper', 'The Nation Thailand', 'https://www.nationthailand.com/', None),
        ('newspaper', 'Khaosod English', 'https://www.khaosodenglish.com/',
         '調査報道で著名'),
        ('pref_police', 'Royal Thai Police', 'https://www.royalthaipolice.go.th/',
         'タイ王国警察'),
        ('city_gov', '在タイ日本国大使館',
         'https://www.th.emb-japan.go.jp/itprtop_ja/index.html', None),
    ],

    # === Vietnam ===
    'VN': [
        ('newspaper', 'VnExpress International',
         'https://e.vnexpress.net/', 'ベトナム主要英字オンライン紙'),
        ('newspaper', 'Tuoi Tre News',
         'https://tuoitrenews.vn/', None),
        ('newspaper', 'Vietnam News', 'https://vietnamnews.vn/',
         '国営英字紙'),
        ('pref_police', 'Vietnam Public Security',
         'https://en.bocongan.gov.vn/', None),
        ('city_gov', '在ベトナム日本国大使館',
         'https://www.vn.emb-japan.go.jp/itpr_ja/00_000001.html', None),
    ],

    # === Laos ===
    'LA': [
        ('newspaper', 'Vientiane Times',
         'https://www.vientianetimes.org.la/', 'ラオス主要英字紙'),
        ('newspaper', 'Laotian Times',
         'https://laotiantimes.com/', None),
        ('city_gov', '在ラオス日本国大使館',
         'https://www.la.emb-japan.go.jp/itpr_ja/00_000001.html', None),
    ],

    # === South Korea ===
    'KR': [
        ('newspaper', '朝鮮日報(Chosun Ilbo)',
         'https://www.chosun.com/', '韓国保守系最大手'),
        ('newspaper', 'ハンギョレ(Hankyoreh)',
         'https://www.hani.co.kr/', '韓国進歩系'),
        ('newspaper', '聯合ニュース(Yonhap News)',
         'https://jp.yna.co.kr/', '韓国通信社・日本語版'),
        ('newspaper', 'The Korea Herald',
         'https://www.koreaherald.com/', '韓国英字紙'),
        ('pref_police', 'Korean National Police Agency',
         'https://www.police.go.kr/eng/index.do', None),
        ('city_gov', '在韓国日本国大使館',
         'https://www.kr.emb-japan.go.jp/itpr_ja/00_000010.html', None),
    ],

    # === China (本土) ===
    'CN': [
        ('newspaper', 'Global Times (環球時報)',
         'https://www.globaltimes.cn/', '中国国営英字紙'),
        ('newspaper', 'Caixin Global',
         'https://www.caixinglobal.com/', '中国独立系経済誌'),
        ('newspaper', '南方都市報',
         'http://www.nandu.com/', '中国南部の調査報道で著名'),
        ('city_gov', '在中華人民共和国日本国大使館',
         'https://www.cn.emb-japan.go.jp/itpr_ja/00_000001.html', None),
    ],

    # === Hong Kong (三合会) ===
    'HK': [
        ('newspaper', 'South China Morning Post (SCMP)',
         'https://www.scmp.com/', '香港主要英字紙'),
        ('newspaper', 'Hong Kong Free Press',
         'https://hongkongfp.com/', '独立報道'),
        ('pref_police', 'Hong Kong Police Force',
         'https://www.police.gov.hk/', None),
        ('city_gov', '在香港日本国総領事館',
         'https://www.hk.emb-japan.go.jp/itprtop_ja/index.html', None),
    ],

    # === Italy (Cosa Nostra / 'Ndrangheta) ===
    'IT': [
        ('newspaper', 'La Repubblica',
         'https://www.repubblica.it/', 'イタリア左派系大手'),
        ('newspaper', 'Corriere della Sera',
         'https://www.corriere.it/', 'イタリア最大紙'),
        ('newspaper', 'Il Fatto Quotidiano',
         'https://www.ilfattoquotidiano.it/', '反マフィア調査報道で著名'),
        ('pref_police', 'Direzione Investigativa Antimafia (DIA)',
         'https://direzioneinvestigativaantimafia.interno.gov.it/',
         '反マフィア捜査局'),
        ('court', 'Direzione Nazionale Antimafia (DNA)',
         'https://www.giustizia.it/', '反マフィア国家対策局'),
        ('city_gov', '在イタリア日本国大使館',
         'https://www.it.emb-japan.go.jp/itpr_ja/00_000071.html', None),
    ],

    # === United States (La Cosa Nostra) ===
    'US': [
        ('newspaper', 'The New York Times',
         'https://www.nytimes.com/', '米国主要紙'),
        ('newspaper', 'The Wall Street Journal',
         'https://www.wsj.com/', '経済・組織犯罪報道'),
        ('newspaper', 'The Washington Post',
         'https://www.washingtonpost.com/', None),
        ('pref_police', 'Federal Bureau of Investigation (FBI)',
         'https://www.fbi.gov/', '連邦捜査局'),
        ('pref_police', 'U.S. Department of Justice',
         'https://www.justice.gov/', '司法省'),
        ('court', 'U.S. Treasury OFAC',
         'https://ofac.treasury.gov/', '財務省外国資産管理局'),
        ('city_gov', '在アメリカ合衆国日本国大使館',
         'https://www.us.emb-japan.go.jp/itprtop_ja/index.html', None),
    ],

    # === International / Mekong (general) ===
    'INTL': [
        ('newspaper', 'Reuters',
         'https://www.reuters.com/', '国際通信社'),
        ('newspaper', 'BBC News',
         'https://www.bbc.com/news', '英国国営放送'),
        ('newspaper', 'Associated Press (AP)',
         'https://apnews.com/', '国際通信社'),
        ('newspaper', 'Agence France-Presse (AFP)',
         'https://www.afp.com/en', '仏国通信社'),
        ('newspaper', 'OCCRP', 'https://www.occrp.org/',
         '国際的組織犯罪調査報道ネットワーク'),
        ('newspaper', 'Bloomberg',
         'https://www.bloomberg.com/', '経済通信社'),
        ('pref_police', 'INTERPOL',
         'https://www.interpol.int/', '国際刑事警察機構'),
        ('other', 'UNODC',
         'https://www.unodc.org/', '国連薬物犯罪事務所'),
    ],

    # === メコン地域(コンパウンド) ===
    'MEKONG': [
        ('newspaper', 'OCCRP', 'https://www.occrp.org/',
         'メコン地域コンパウンド調査の主要メディア'),
        ('newspaper', 'Al Jazeera English',
         'https://www.aljazeera.com/', None),
        ('newspaper', 'Radio Free Asia',
         'https://www.rfa.org/english/', None),
        ('npo', 'Global Anti-Scam Org (GASO)',
         'https://www.globalantiscam.org/',
         '詐欺コンパウンド被害者支援'),
        ('other', 'UNODC',
         'https://www.unodc.org/', '国連薬物犯罪事務所(メコン地域監視)'),
    ],
}


# slug → country code(海外拠点のみ)
SLUG_TO_COUNTRY = {
    'philippines_luffy_base': 'PH',
    'cambodia_compounds_link': 'KH',
    'myanmar_compounds_link': 'MM',
    'thailand_tokuryu_base': 'TH',
    'vietnam_tokuryu_base': 'VN',
    'laos_tokuryu_base': 'LA',
    'tokuryu_kankoku_link': 'KR',
    'drug_korea_route': 'KR',
    'drug_china_southeast': 'CN',
    'intl_triads_hk': 'HK',
    'intl_cosa_nostra_italy': 'IT',
    'intl_ndrangheta_italy': 'IT',
    'intl_la_cosa_nostra_us': 'US',
    'intl_mekong_compounds_ref': 'MEKONG',
    'roman_sagi_centers': 'INTL',
    # Phase 53 Manila chaos
    'manila_jollibee': 'PH',
    'manila_jeepney': 'PH',
    'manila_intramuros': 'PH',
    # 国際的 / グローバル拠点
    'ofac_treasury_designation': 'US',  # OFAC は米国財務省
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    # ensure local_media table exists
    cur.execute('''
      CREATE TABLE IF NOT EXISTS local_media (
        id INTEGER PRIMARY KEY,
        site_id INTEGER NOT NULL,
        kind TEXT,
        name TEXT NOT NULL,
        url TEXT,
        note TEXT,
        ord INTEGER DEFAULT 100
      )
    ''')
    sites = {row[1]: row[0] for row in cur.execute('SELECT id, slug FROM site')}
    inserted = 0; assigned = 0; missing = []
    for slug, cc in SLUG_TO_COUNTRY.items():
        sid = sites.get(slug)
        if sid is None:
            missing.append(slug); continue
        media = INTL_MEDIA_BY_COUNTRY.get(cc, [])
        if not media:
            continue
        # 既存のエントリ(同名)を一度削除して入れ直す
        for kind, name, url, note in media:
            cur.execute('DELETE FROM local_media WHERE site_id=? AND name=?',
                        (sid, name))
        ord_ = 10
        for kind, name, url, note in media:
            cur.execute(
                'INSERT INTO local_media(site_id, kind, name, url, note, ord) '
                'VALUES (?,?,?,?,?,?)',
                (sid, kind, name, url, note, ord_))
            ord_ += 5
            inserted += 1
        assigned += 1
    con.commit()
    total = cur.execute('SELECT COUNT(*) FROM local_media').fetchone()[0]
    sites_with = cur.execute(
        'SELECT COUNT(DISTINCT site_id) FROM local_media'
    ).fetchone()[0]
    print(f'phase47_intl_media: +{inserted} intl rows across {assigned} overseas sites')
    print(f'  total local_media: {total} across {sites_with} sites')
    if missing: print(f'  WARN: missing slugs: {missing}')
    con.close()


if __name__ == '__main__':
    main()
