"""Phase 43: 主要な事実の検証修正(WebSearchで確認済の正しい日付/数値)。

WebSearch で複数の主要報道(日経・西日本新聞・神戸新聞・Treasury・
Federal Register)で確認した事実に基づき、誤った日付・数値を修正。

主な修正:
  - 工藤會本部解体: 2019-07-04 → 2019-11-22(実際の解体着工は11月)
  - OFAC TCO 指定: 2013-02-23 → 2013-02-15(Federal Register 公示日)
  - 工藤會本部 売却合意: 2019-09-25 を追記
  - 旦過市場火災 規模: 4月 1924m²/42店, 8月 3324m²/45店(規模数値の正確化)

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    fixes = 0

    # 1) 工藤會本部解体: 2019-07 → 2019-11-22
    # Events 10, 11, 129, 318, 319 にて日付修正
    events_fix = cur.execute('''
        UPDATE event
        SET happened_on = '2019-11-22'
        WHERE happened_on IN ('2019-07', '2019-07-04')
          AND (title LIKE '%解体%' OR title LIKE '%金看板%' OR title LIKE '%神岳交差点%' OR title LIKE '%馬借%')
    ''').rowcount
    print(f'本部解体日付修正: {events_fix} events')
    fixes += events_fix

    # 2) OFAC TCO 指定日付修正
    ofac_fix = cur.execute('''
        UPDATE event
        SET happened_on = '2013-02-15'
        WHERE happened_on = '2013-02-23'
    ''').rowcount
    print(f'OFAC 日付修正: {ofac_fix} events')
    fixes += ofac_fix

    chron_ofac = cur.execute('''
        UPDATE chronicle
        SET year_label = '2013-02-15',
            body = REPLACE(body, '2013-02-23', '2013-02-15')
        WHERE year_label = '2013-02-23'
    ''').rowcount
    print(f'OFAC chronicle 修正: {chron_ofac}')
    fixes += chron_ofac

    chron_kaitai = cur.execute('''
        UPDATE chronicle
        SET year_label = '2019-11-22',
            body = REPLACE(REPLACE(body, '2019年7月', '2019年11月'), '7-04', '11-22')
        WHERE year_label LIKE '2019-07%' AND title LIKE '%解体%'
    ''').rowcount
    print(f'本部解体 chronicle 修正: {chron_kaitai}')
    fixes += chron_kaitai

    # 3) 工藤會本部 売却合意(2019-09-25)を新しい event として追加
    # 既存に近い event があれば置換、なければ INSERT
    cur.execute('''
        SELECT id FROM site WHERE slug = 'kudokai_hq_kandake'
    ''')
    row = cur.fetchone()
    if row:
        site_id = row[0]
        # Check if already exists
        existing = cur.execute('''
            SELECT id FROM event WHERE site_id = ? AND happened_on = '2019-09-25'
        ''', (site_id,)).fetchone()
        if not existing:
            cur.execute('''
                INSERT INTO event(kind, happened_on, site_id, title, summary,
                                  era_tag, faction_tag, severity)
                VALUES (?,?,?,?,?,?,?,?)
            ''', ('lore', '2019-09-25', site_id,
                  '本部 売却合意成立',
                  '北九州市と工藤會で本部建物の売却合意が成立(売却額1億円)。'
                  '民間事業者への売却・年度内解体・暴追運動推進センター被害者補償への一部充当が確定。',
                  '解体後', '工藤組系', 4))
            fixes += 1
            print('本部売却合意 event 追加')

    # 4) Site notes 修正: 神岳本部の解体日
    note_fix = cur.execute('''
        UPDATE site
        SET notes = REPLACE(REPLACE(notes, '2019-07-04 解体着手', '2019-11-22 解体着手'),
                          '2019年8月までに更地化', '2020年初頭までに更地化')
        WHERE slug = 'kudokai_hq_kandake'
    ''').rowcount
    print(f'本部 site notes 修正: {note_fix}')
    fixes += note_fix

    # 5) 旦過市場 火災規模数値を notes に正確化
    old_str = '2022-04-19 と 2022-08-10 の二度の大規模火災で北側街区が大きく失われた'
    new_str = ('2022-04-19(1,924m²・42店舗焼失)と 2022-08-10(3,324m²・45店舗焼失)の'
               '二度の大規模火災で北側街区の大半が失われた')
    tanga_fix = cur.execute(
        "UPDATE site SET notes = REPLACE(notes, ?, ?) WHERE slug = 'tanga_market'",
        (old_str, new_str)
    ).rowcount
    print(f'旦過市場 notes 修正: {tanga_fix}')
    fixes += tanga_fix

    con.commit()
    print(f'\nTotal fixes applied: {fixes}')
    con.close()


if __name__ == '__main__':
    main()
