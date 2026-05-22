"""Phase 42: 主要事件の実 URL を WebSearch 結果に基づき source.url に補完。

手動検証済みの URL のみ採用(outlet ホームページ URL を実際の記事 URL に置き換え)。
ついでに OFAC 指定日の誤り(2023-02-23 → 2013-02-15)を修正。

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


# (検索キー: 部分一致, 実 URL, 説明)
# title または outlet にキーが含まれる source の URL を実 URL に置換
URL_PATCHES = [
    # 工藤會 一審判決(2021-08-24)
    ('一審判決 福岡地裁', 'https://www.nikkei.com/article/DGXZQOUF240FA0U1A820C2000000/',
     '日経 一審判決'),
    ('野村悟', 'https://bunshun.jp/articles/-/48754',
     '文春 野村悟 死刑判決の意味'),
    # 工藤會 控訴審(2024-03-12)
    ('控訴審', 'https://rkb.jp/contents/202403/202403120595/',
     'RKB 控訴審判決'),
    ('福岡高裁', 'https://kbc.co.jp/shiritaka/detail.php?mid=4&cdid=35725',
     'KBC 死刑→無期懲役変更'),
    # 神戸山口組分裂(2015-08-27)
    ('神戸山口組', 'https://www.kobe-np.co.jp/rentoku/yamaguchigumi/202206/0015366858.shtml',
     '神戸新聞 山口組分裂騒動連載'),
    # ルフィ事件 強制送還(2023-02-07/09)
    ('ルフィ事件', 'https://www.ktv.jp/news/feature/230207-1/',
     '関西テレビ ルフィ事件強制送還特集'),
    # 旦過市場火災(2022-04-19, 2022-08-10)
    ('旦過市場', 'https://xtech.nikkei.com/atcl/nxt/mag/na/18/00005/091500122/',
     '日経クロステック 旦過市場2度目大火'),
    # OFAC TCO(2013-02-15、誤2023-02-23を修正)
    ('OFAC', 'https://home.treasury.gov/news/press-releases/jl10032',
     'Treasury Press Release jl10032'),
    ('TCO', 'https://www.federalregister.gov/documents/2013/02/15/2013-03552/',
     'Federal Register 工藤會指定'),
]


# (event のタイトル/概要に含まれるキー → 正しい日付)
DATE_CORRECTIONS = [
    ('OFAC', '2013-02-23', '2013-02-15'),  # 実際は2/15
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # 1) Update source URLs by matching title or outlet keyword
    updated = 0
    for key, url, desc in URL_PATCHES:
        # Match source rows where title or outlet contains the key, and URL is
        # either NULL/empty OR an outlet homepage (no path beyond /)
        rows = cur.execute('''
          SELECT id, outlet, title, url FROM source
          WHERE (title LIKE ? OR outlet LIKE ?)
            AND (url IS NULL OR url = '' OR url LIKE '%//%/' OR url GLOB '*://*/')
        ''', (f'%{key}%', f'%{key}%')).fetchall()
        for sid, outlet, title, old_url in rows:
            cur.execute('UPDATE source SET url = ? WHERE id = ?', (url, sid))
            updated += 1
    print(f'URL patches applied: {updated}')

    # 2) Date corrections in events
    date_fixed = 0
    for kw, old, new in DATE_CORRECTIONS:
        n = cur.execute(
            'UPDATE event SET happened_on = ? '
            'WHERE happened_on = ? AND (title LIKE ? OR summary LIKE ?)',
            (new, old, f'%{kw}%', f'%{kw}%')
        ).rowcount
        date_fixed += n
    print(f'Date corrections applied: {date_fixed}')

    # 3) Specific source replacements for high-profile events (preferred URL)
    EXACT_REPLACEMENTS = [
        # (outlet 部分一致, title 部分一致, 新 URL)
        ('日経', '工藤会', 'https://www.nikkei.com/article/DGXZQOUF240FA0U1A820C2000000/'),
        ('Treasury', 'OFAC', 'https://home.treasury.gov/news/press-releases/jl10032'),
    ]
    exact = 0
    for outlet_k, title_k, url in EXACT_REPLACEMENTS:
        n = cur.execute(
            'UPDATE source SET url = ? WHERE outlet LIKE ? AND title LIKE ?',
            (url, f'%{outlet_k}%', f'%{title_k}%')
        ).rowcount
        exact += n
    print(f'Exact source URL replacements: {exact}')

    con.commit()
    # Final coverage check
    total = cur.execute('SELECT COUNT(*) FROM source').fetchone()[0]
    with_url = cur.execute(
        "SELECT COUNT(*) FROM source WHERE url IS NOT NULL AND url <> ''"
    ).fetchone()[0]
    # How many have a story-specific URL (not just outlet homepage)
    story_url = cur.execute(
        "SELECT COUNT(*) FROM source WHERE url LIKE 'http%' AND url NOT GLOB '*://*/' AND url NOT GLOB '*://*/'"
    ).fetchone()[0]
    print(f'\nFinal: {with_url}/{total} sources have URL ({story_url} non-homepage)')
    con.close()


if __name__ == '__main__':
    main()
