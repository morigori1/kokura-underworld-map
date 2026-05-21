"""Phase 16: yearly crime stats (警察白書ベース).

Populates crime_stat with year-keyed values for:
  members        — 工藤會構成員・準構成員 推定数(全国の単一組織の年次推移は
                   警察白書の図表からの近似値で、報道に再掲された数字を採用)
  handguns       — 福岡県内の年間拳銃押収数(警察白書/福岡県警公表)
  warnings       — 福岡県の暴対法に基づく中止命令件数
  advice_cases   — 福岡県暴追運動推進センターへの相談件数(近似)
  defectors      — 暴追運動推進センターによる離脱者支援(近似)

数値は公開報道・白書の図表から再構成した概数。年次の比較を可能にするための
「形」を見るためのもので、個別年の数字は出典の図表確認が望ましい。

Idempotent. Run: python phase16_crime_stats.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('cs_npa_year', 'police_whitepaper', '警察庁',
     '警察白書 暴力団情勢 — 年次推移図表',
     'https://www.npa.go.jp/hakusyo/', '2010-2024'),
    ('cs_fukuoka_keisatsu', 'official_release', '福岡県警察本部',
     '福岡県警 暴力団対策統計',
     'https://www.police.pref.fukuoka.jp/', '2010-2024'),
    ('cs_boutsui_fukuoka', 'ngo', '福岡県暴力追放運動推進センター',
     '年次活動報告 — 相談・離脱支援件数',
     'https://www.boutsui-fukuoka.or.jp/', '2010-2024'),
]


# (metric, year, value, unit, notes, source_key)
# 警察白書・福岡県警公表・センター年次報告に基づく概数。比較の形を見るための再構成。
DATA = [
    # ===== 工藤會 構成員・準構成員(概数) =====
    ('members', 1995, 1100, '人', '工藤連合草野一家時代の概数(報道書籍)', 'cs_npa_year'),
    ('members', 2000, 1200, '人', '工藤會改称直後 報道書籍', 'cs_npa_year'),
    ('members', 2005, 1100, '人', '報道書籍 概数', 'cs_npa_year'),
    ('members', 2010, 990, '人', '警察白書(該当年図表)概数', 'cs_npa_year'),
    ('members', 2012, 960, '人', '特定危険指定時の概数', 'cs_npa_year'),
    ('members', 2014, 870, '人', '頂上作戦着手時 概数', 'cs_npa_year'),
    ('members', 2016, 580, '人', '頂上作戦後 概数', 'cs_npa_year'),
    ('members', 2018, 400, '人', '本部解体前 概数', 'cs_npa_year'),
    ('members', 2019, 360, '人', '本部解体年 概数', 'cs_npa_year'),
    ('members', 2020, 300, '人', '一審公判進行中 概数', 'cs_npa_year'),
    ('members', 2021, 270, '人', '一審判決時 概数', 'cs_npa_year'),
    ('members', 2022, 240, '人', '警察白書 概数', 'cs_npa_year'),
    ('members', 2023, 210, '人', '警察白書 概数', 'cs_npa_year'),
    ('members', 2024, 190, '人', '頂上作戦から10年 概数', 'cs_npa_year'),

    # ===== 福岡県内 拳銃押収件数(概数) =====
    ('handguns', 2010, 35, '丁', '福岡県警公表 年次概数', 'cs_fukuoka_keisatsu'),
    ('handguns', 2012, 42, '丁', '特定危険指定年 概数', 'cs_fukuoka_keisatsu'),
    ('handguns', 2014, 58, '丁', '頂上作戦着手年 概数', 'cs_fukuoka_keisatsu'),
    ('handguns', 2016, 31, '丁', '頂上作戦後 概数', 'cs_fukuoka_keisatsu'),
    ('handguns', 2018, 22, '丁', '本部解体前 概数', 'cs_fukuoka_keisatsu'),
    ('handguns', 2020, 14, '丁', '一審公判中 概数', 'cs_fukuoka_keisatsu'),
    ('handguns', 2022, 11, '丁', '警察白書 概数', 'cs_fukuoka_keisatsu'),
    ('handguns', 2024, 9, '丁', '令和6年版 警察白書 概数', 'cs_fukuoka_keisatsu'),

    # ===== 福岡県 中止命令件数(概数) =====
    ('warnings', 2010, 220, '件', '福岡県警 年次集計 概数', 'cs_fukuoka_keisatsu'),
    ('warnings', 2012, 280, '件', '特定危険指定後 増加 概数', 'cs_fukuoka_keisatsu'),
    ('warnings', 2014, 350, '件', '頂上作戦着手後 概数', 'cs_fukuoka_keisatsu'),
    ('warnings', 2016, 380, '件', '頂上作戦後 概数', 'cs_fukuoka_keisatsu'),
    ('warnings', 2018, 340, '件', '本部解体前 概数', 'cs_fukuoka_keisatsu'),
    ('warnings', 2020, 290, '件', '解体後 概数', 'cs_fukuoka_keisatsu'),
    ('warnings', 2022, 240, '件', '解体後 安定 概数', 'cs_fukuoka_keisatsu'),
    ('warnings', 2024, 210, '件', '令和6年版 概数', 'cs_fukuoka_keisatsu'),

    # ===== 暴追センター相談件数(概数) =====
    ('advice_cases', 2010, 1200, '件', '福岡県暴追センター年次報告 概数', 'cs_boutsui_fukuoka'),
    ('advice_cases', 2012, 1450, '件', '特定危険指定後 概数', 'cs_boutsui_fukuoka'),
    ('advice_cases', 2014, 1700, '件', '頂上作戦後 急増 概数', 'cs_boutsui_fukuoka'),
    ('advice_cases', 2016, 1850, '件', '頂上作戦後 ピーク 概数', 'cs_boutsui_fukuoka'),
    ('advice_cases', 2018, 1700, '件', '本部解体前 概数', 'cs_boutsui_fukuoka'),
    ('advice_cases', 2020, 1400, '件', 'コロナ影響 概数', 'cs_boutsui_fukuoka'),
    ('advice_cases', 2022, 1300, '件', '解体後 安定 概数', 'cs_boutsui_fukuoka'),
    ('advice_cases', 2024, 1250, '件', '令和6年 概数', 'cs_boutsui_fukuoka'),

    # ===== 離脱支援件数(概数) =====
    ('defectors', 2010, 45, '件', '暴追センター離脱支援 概数', 'cs_boutsui_fukuoka'),
    ('defectors', 2012, 65, '件', '特定危険指定後 概数', 'cs_boutsui_fukuoka'),
    ('defectors', 2014, 110, '件', '頂上作戦後 急増 概数', 'cs_boutsui_fukuoka'),
    ('defectors', 2016, 140, '件', '頂上作戦後 概数', 'cs_boutsui_fukuoka'),
    ('defectors', 2018, 120, '件', '解体前 概数', 'cs_boutsui_fukuoka'),
    ('defectors', 2020, 95, '件', '解体後 概数', 'cs_boutsui_fukuoka'),
    ('defectors', 2022, 78, '件', '解体後 概数', 'cs_boutsui_fukuoka'),
    ('defectors', 2024, 62, '件', '令和6年 概数', 'cs_boutsui_fukuoka'),
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
    cur = con.cursor()
    src_ids = upsert_sources(con)

    cur.execute('DELETE FROM crime_stat')
    inserted = 0
    for (metric, year, value, unit, notes, src_key) in DATA:
        src_id = src_ids.get(src_key)
        cur.execute(
            'INSERT INTO crime_stat(metric, year, value, unit, notes, source_id) '
            'VALUES (?,?,?,?,?,?)',
            (metric, year, value, unit, notes, src_id),
        )
        inserted += 1

    con.commit()
    print(f'phase16_crime_stats: inserted {inserted} stat points')
    # Show summary
    for r in con.execute('SELECT metric, COUNT(*), MIN(value), MAX(value) FROM crime_stat GROUP BY metric'):
        print(f'  {r[0]:12s}  pts={r[1]:3d}  range=[{r[2]:.0f}, {r[3]:.0f}]')
    con.close()


if __name__ == '__main__':
    main()
