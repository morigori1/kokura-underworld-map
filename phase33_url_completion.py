"""Phase 33: 出典 URL 補完 — outlet ホームページ URL を埋める。

phase8(og:image 取得)を機能させるために、URL の無い source に対して
outlet 名から推測される公式ホームページ URL を補填する。

og:image はストーリー固有ではなく outlet 共通ロゴになるが、
事件カードに視覚的識別子が付与される効果がある。

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


# (outlet 名のキーワード, 公式ホームページ URL)
# キーワードは outlet 列に部分一致でマッチさせる
OUTLET_URLS = [
    ('NHK',                   'https://www.nhk.or.jp/'),
    ('西日本新聞',            'https://www.nishinippon.co.jp/'),
    ('朝日新聞',              'https://www.asahi.com/'),
    ('毎日新聞',              'https://mainichi.jp/'),
    ('読売新聞',              'https://www.yomiuri.co.jp/'),
    ('産経新聞',              'https://www.sankei.com/'),
    ('日経新聞',              'https://www.nikkei.com/'),
    ('共同通信',              'https://www.kyodo.co.jp/'),
    ('時事通信',              'https://www.jiji.com/'),
    ('神奈川新聞',            'https://www.kanaloco.jp/'),
    ('千葉日報',              'https://www.chibanippo.co.jp/'),
    ('茨城新聞',              'https://ibarakinews.jp/'),
    ('下野新聞',              'https://www.shimotsuke.co.jp/'),
    ('上毛新聞',              'https://www.jomo-news.co.jp/'),
    ('中日新聞',              'https://www.chunichi.co.jp/'),
    ('神戸新聞',              'https://www.kobe-np.co.jp/'),
    ('中国新聞',              'https://www.chugoku-np.co.jp/'),
    ('京都新聞',              'https://www.kyoto-np.co.jp/'),
    ('沖縄タイムス',          'https://www.okinawatimes.co.jp/'),
    ('琉球新報',              'https://ryukyushimpo.jp/'),
    ('大分合同新聞',          'https://www.oita-press.co.jp/'),
    ('熊本日日新聞',          'https://kumanichi.com/'),
    ('佐賀新聞',              'https://www.saga-s.co.jp/'),
    ('新潟日報',              'https://www.niigata-nippo.co.jp/'),
    ('福井新聞',              'https://www.fukuishimbun.co.jp/'),
    ('Reuters',               'https://www.reuters.com/'),
    ('BBC',                   'https://www.bbc.com/'),
    ('NYT',                   'https://www.nytimes.com/'),
    ('Guardian',              'https://www.theguardian.com/'),
    ('AP',                    'https://apnews.com/'),
    ('AFP',                   'https://www.afp.com/'),
    ('Japan Times',           'https://www.japantimes.co.jp/'),
    ('Diplomat',              'https://thediplomat.com/'),
    ('Bloomberg',             'https://www.bloomberg.com/'),
    ('OCCRP',                 'https://www.occrp.org/'),
    ('FBI',                   'https://www.fbi.gov/'),
    ('ITmedia',               'https://www.itmedia.co.jp/'),
    ('創',                    'https://www.tsukuru.co.jp/'),  # 月刊『創』
    ('警察庁',                'https://www.npa.go.jp/'),
    ('警視庁',                'https://www.keishicho.metro.tokyo.lg.jp/'),
    ('福岡県警',              'https://www.police.pref.fukuoka.jp/'),
    ('兵庫県警',              'https://www.police.pref.hyogo.lg.jp/'),
    ('国会',                  'https://kokkai.ndl.go.jp/'),
    ('国家公安委員会',        'https://www.npsc.go.jp/'),
    ('金融庁',                'https://www.fsa.go.jp/'),
    ('全国銀行協会',          'https://www.zenginkyo.or.jp/'),
    ('OFAC',                  'https://ofac.treasury.gov/'),
    ('国土交通省',            'https://www.mlit.go.jp/'),
    ('厚生労働省',            'https://www.mhlw.go.jp/'),
    ('文部科学省',            'https://www.mext.go.jp/'),
    ('北九州市',              'https://www.city.kitakyushu.lg.jp/'),
    ('福岡県',                'https://www.pref.fukuoka.lg.jp/'),
    ('福岡市',                'https://www.city.fukuoka.lg.jp/'),
    ('東映',                  'https://www.toei.co.jp/'),
    ('松竹',                  'https://www.shochiku.co.jp/'),
    ('東宝',                  'https://www.toho.co.jp/'),
    ('セガ',                  'https://www.sega.co.jp/'),
    ('HBO',                   'https://www.hbo.com/'),
    ('FBS',                   'https://www.fbs.co.jp/'),
    ('RKB',                   'https://rkb.jp/'),
    ('東海テレビ',            'https://tokai-tv.com/'),
    ('国家公安',              'https://www.npsc.go.jp/'),
    ('国家公安委員会',        'https://www.npsc.go.jp/'),
    ('米国大使館',            'https://jp.usembassy.gov/'),
    ('福岡県暴力追放',        'https://www.boutsui-fukuoka.or.jp/'),
    ('全国暴力追放',          'https://www.zenboutsui.jp/'),
    ('北九州市暴追',          'https://www.city.kitakyushu.lg.jp/'),
    ('東京地裁',              'https://www.courts.go.jp/'),
    ('福岡地裁',              'https://www.courts.go.jp/'),
    ('福岡高裁',              'https://www.courts.go.jp/'),
    ('最高裁',                'https://www.courts.go.jp/'),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    # Get sources with no URL
    rows = cur.execute(
        "SELECT id, outlet FROM source WHERE url IS NULL OR url = ''"
    ).fetchall()
    print(f'Found {len(rows)} sources without URL')

    updated = 0
    for source_id, outlet in rows:
        if not outlet:
            continue
        matched_url = None
        # Find the first keyword that matches in outlet name
        for keyword, url in OUTLET_URLS:
            if keyword in outlet:
                matched_url = url
                break
        if matched_url:
            cur.execute('UPDATE source SET url=? WHERE id=?', (matched_url, source_id))
            updated += 1
    con.commit()
    print(f'phase33_url_completion: updated {updated} source URLs')
    # Show by outlet
    print('\nURL coverage by outlet:')
    for r in con.execute(
        'SELECT outlet, COUNT(*), '
        '       SUM(CASE WHEN url IS NULL OR url = \'\' THEN 0 ELSE 1 END) '
        'FROM source GROUP BY outlet '
        'HAVING COUNT(*) >= 3 ORDER BY 2 DESC LIMIT 20'
    ):
        print(f'  {r[0][:40]:40s}  total={r[1]:3d}  with_url={r[2]:3d}')
    con.close()


if __name__ == '__main__':
    main()
