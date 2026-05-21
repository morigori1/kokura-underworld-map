"""Insert testimony / ruling-reasoning excerpts.

Editorial policy:
  - We do not fabricate direct quotes from court rulings or victims.
  - When we use a "quote" field, it is either:
      (a) a faithful summary of a publicly available statement (court press
          conference summary, prosecutor briefing, council statement), marked
          with attribution and not bracketed as a verbatim quote; OR
      (b) a verbatim quote when it has been widely reported and attributed in
          major outlets, kept short and in 「」.
  - Victims are referred to by their public role (元漁協理事 / 元警察官 /
    看護師 / 歯科医師) — never by name.
  - Each row links to a `source` row created here or in phase6.

Idempotent. Run: python phase9_testimony.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


# Supplementary sources (phase6 already inserted ruling sources).
SOURCES = [
    # key, kind, outlet, title, url, published_on
    ('src_ruling_summary_2021',
     'ruling', '福岡地方裁判所',
     '工藤會トップ判決 — 判決要旨(2021-08-24 言渡)',
     'https://www.courts.go.jp/', '2021-08-24'),
    ('src_high_ruling_summary_2024',
     'ruling', '福岡高等裁判所',
     '工藤會トップ控訴審 — 判決要旨(2024-03-12 言渡)',
     'https://www.courts.go.jp/', '2024-03-12'),
    ('src_pros_briefing_2021',
     'news', '西日本新聞 / 共同通信',
     '福岡地検 記者会見(2021-08-24 一審判決後)',
     None, '2021-08-24'),
    ('src_victim_council_2021',
     'news', '西日本新聞',
     '市民襲撃被害者支援団体声明',
     None, '2021-08-24'),
    ('src_npa_whitepaper',
     'police_whitepaper', '警察庁',
     '令和の警察白書 — 工藤會対策の経緯',
     'https://www.npa.go.jp/hakusyo/', '2023'),
]


# site_slug, source_key, role, speaker_label, year, quote
ROWS = [
    # 1998 漁協理事射殺
    ('attack_1998_ashiya_fisheries', 'src_ruling_summary_2021',
     'judge', '福岡地裁判決要旨より', '2021',
     '1998年の元漁協理事射殺は、漁業権をめぐる対立を背景に工藤會幹部らが企てた '
     '組織的犯行であり、野村被告は組のトップとしてこれを了承していたと認定された '
     '(判決要旨)。'),
    # 2012 元警察官襲撃
    ('attack_2012_ex_officer', 'src_ruling_summary_2021',
     'judge', '福岡地裁判決要旨より', '2021',
     '2012年の元警察官襲撃は、警察組織への威迫を目的として工藤會の組織的判断の下に '
     '行われたものと認定され、被告らはその指示・了承に関与したとされた(判決要旨)。'),
    # 2013 看護師襲撃
    ('attack_2013_nurse', 'src_ruling_summary_2021',
     'judge', '福岡地裁判決要旨より', '2021',
     '2013年の看護師襲撃は、特定の医療関係者一族への一連の威迫の中で行われたと '
     '判断された(判決要旨)。'),
    # 2014 歯科医師襲撃
    ('attack_2014_dentist', 'src_ruling_summary_2021',
     'judge', '福岡地裁判決要旨より', '2021',
     '2014年の歯科医師襲撃は、医療関係者一族への一連の威迫の集大成として位置づけられ、'
     '本事件をきっかけに警察による「頂上作戦」が本格化した(判決要旨)。'),
    # 訴訟全体への高裁判断
    ('kudokai_hq_kandake', 'src_high_ruling_summary_2024',
     'judge', '福岡高裁判決要旨より', '2024',
     '一審の野村被告に対する死刑判決については、状況証拠の積み上げに基づく '
     '事実認定の在り方に一審と判断が分かれ、結論として死刑判決を破棄し '
     '無期懲役を言い渡した。田上被告の無期懲役は維持(判決要旨)。'),
    # 検察会見
    ('kudokai_hq_kandake', 'src_pros_briefing_2021',
     'prosecutor', '福岡地検 記者会見要旨', '2021',
     '本判決は、指定暴力団のトップを「事件の首謀者」として刑事責任を問う '
     '異例の捜査・公判の結節点であり、市民を直接の標的とした組織暴力に対する '
     '司法判断の重要な前例となる(記者会見の趣旨)。'),
    # 被害者支援団体声明
    ('kudokai_hq_kandake', 'src_victim_council_2021',
     'family', '被害者・支援団体声明 要旨', '2021',
     '長年にわたり市民を直接の標的とした組織犯罪に司法が踏み込んだ意義は大きい。'
     '一方、被害者と遺族の傷は容易に癒えない、として継続的な被害者支援を求めた '
     '(声明の趣旨)。'),
    # 警察白書からの位置づけ
    ('kudokai_hq_kandake', 'src_npa_whitepaper',
     'police', '警察庁 警察白書 要旨', '2023',
     '工藤會は全国で唯一「特定危険指定暴力団」に指定された組織であり、'
     '頂上作戦以降の構成員数の減少が確認されている。一方、市民・事業者への '
     '威迫の手口は依然として残存し、対策の継続が必要と整理された(白書の趣旨)。'),
]


def upsert_sources(con) -> dict[str, int]:
    cur = con.cursor()
    keymap = {}
    for key, kind, outlet, title, url, pub in SOURCES:
        cur.execute(
            "DELETE FROM source WHERE outlet=? AND title=? AND COALESCE(published_on,'')=?",
            (outlet, title, pub or ''),
        )
        cur.execute(
            'INSERT INTO source(kind, outlet, title, url, published_on) '
            'VALUES (?,?,?,?,?)',
            (kind, outlet, title, url, pub),
        )
        keymap[key] = cur.lastrowid
    return keymap


def main():
    con = sqlite3.connect(DB)
    s_ids = {row[0]: row[1] for row in con.execute('SELECT slug, id FROM site')}
    src_ids = upsert_sources(con)

    con.execute("DELETE FROM testimony")  # full refresh; only phase9 writes testimony

    inserted = 0
    for slug, src_key, role, speaker, year, quote in ROWS:
        site_id = s_ids.get(slug)
        if site_id is None:
            print(f'  WARN: site slug not found: {slug} (skipped)')
            continue
        src_id = src_ids.get(src_key)
        con.execute(
            'INSERT INTO testimony(site_id, role, speaker_label, year, quote, source_id) '
            'VALUES (?,?,?,?,?,?)',
            (site_id, role, speaker, year, quote, src_id),
        )
        inserted += 1

    con.commit()
    n = con.execute('SELECT COUNT(*) FROM testimony').fetchone()[0]
    print(f'phase9_testimony: inserted {inserted}; total testimony={n}')
    con.close()


if __name__ == '__main__':
    main()
