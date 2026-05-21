"""Local-life snippets for each site.

These are short editorial paragraphs about the *current state of the street* —
how the area lives now, after (or alongside) the violence. They give the map a
texture beyond the criminal narrative.

Each snippet is anchored to a site and carries an outlet label + URL (where the
canonical link is known). Editorial policy follows phase9: paraphrase rather
than fabricate quotes.

Idempotent. Run: python phase10_local_life.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


# site_slug, ord, topic, text, source_label, source_url
SNIPPETS = [
    # ---- 工藤會本部跡 ----
    ('kudokai_hq_kandake', 10, '跡地のいま',
     '本部跡は2019年8月の解体後、競売・売却を経て民有地となった。'
     '神岳1丁目は周辺に小倉警察署があり、徒歩圏に小倉北区役所・市民会館が並ぶ '
     '行政・住宅混在エリア。日常的には目立つ警備はなく、看板のない区画が残る。',
     '西日本新聞', None),
    ('kudokai_hq_kandake', 20, '街の空気',
     '工藤會本部解体は地域住民が長年求めてきたもので、地元自治会・暴力追放運動 '
     '北九州市民会議などが「街を取り戻す」象徴として位置づけた。'
     '2024年時点でも、市と県警は事業者への防犯講習・暴排相談を継続している。',
     '北九州市暴力追放運動推進会議', None),

    # ---- 旦過市場 ----
    ('tanga_market', 10, '2022年 二度の大火',
     '2022年4月19日と同8月10日、旦過市場で大規模火災が発生。'
     '北九州を象徴する戦後闇市起源の市場の北側街区が大きく焼失した。'
     '原因は捜査が継続したが、工藤會事件との直接の関連は公式には認定されていない。',
     'NHK / 西日本新聞', None),
    ('tanga_market', 20, '再整備と暫定店舗',
     '火災後、市場組合は暫定店舗での営業を続けながら段階的に再整備を進めた。'
     '北九州市は商店街・観光と防災を両立する再整備計画を策定。'
     '昭和の闇市から続く小路は一部失われたが、観光客と地元客の往来は戻っている。',
     '北九州市・旦過市場商店街振興組合', None),

    # ---- 魚町銀天街 ----
    ('uomachi_arcade', 10, '日本初のアーケード',
     '1951年に完成した日本初の本格的アーケード商店街。'
     '小倉駅と旦過市場を結ぶ動線で、現在もイベントや常設店が街の顔を担う。'
     '夜間の人通りはコロナ後に一定程度回復している。',
     '北九州市・魚町商店街振興組合', None),

    # ---- 堺町歓楽街 ----
    ('sakaimachi_quarter', 10, '九州有数の歓楽街',
     '小倉北区堺町1〜2丁目に飲食・接待店が密集する九州有数の歓楽街。'
     '長年、工藤會傘下のショバ代徴収・トラブル介入の温床と報じられてきたが、'
     '頂上作戦以降は店舗側の暴排対応(暴排ステッカー掲示・通報窓口整備)が広がった。',
     '西日本新聞', None),
    ('sakaimachi_quarter', 20, '不当要求の現状',
     '福岡県警と暴追運動センターによる事業者向け相談窓口が継続稼働。'
     'みかじめ料・用心棒料に類する不当要求は減少傾向と報じられる一方、'
     '違反勧誘・不払い名目の威迫は依然として相談事例に現れている。',
     '福岡県警察 / 暴追運動推進センター', None),

    # ---- 小倉駅 ----
    ('kokura_station', 10, '街のハブ',
     '北九州市の中心ターミナル駅。新幹線・在来線・モノレールが集結し、'
     '小倉北区中心市街の再開発の起点になっている。本マップの拠点群はこの駅から '
     '徒歩〜タクシー10分圏内に収まる。',
     'JR九州 / 北九州市', None),

    # ---- 芦屋町 ----
    ('attack_1998_ashiya_fisheries', 10, '町のいま',
     '芦屋町は遠賀川河口の漁港町。漁協は再編を経て地域漁業を続けている。'
     '1998年の事件は町の現代史に刻まれた重大事件として地元紙に繰り返し取り上げられ、'
     '判決の節目ごとに当時の関係者の高齢化と区切りが報じられた。',
     '西日本新聞', None),
]


def main():
    con = sqlite3.connect(DB)
    s_ids = {row[0]: row[1] for row in con.execute('SELECT slug, id FROM site')}

    con.execute('DELETE FROM life_snippet')

    inserted = 0
    for slug, ord_, topic, text, label, url in SNIPPETS:
        site_id = s_ids.get(slug)
        if site_id is None:
            print(f'  WARN: site slug not found: {slug} (skipped)')
            continue
        con.execute(
            'INSERT INTO life_snippet(site_id, ord, topic, text, source_label, source_url) '
            'VALUES (?,?,?,?,?,?)',
            (site_id, ord_, topic, text, label, url),
        )
        inserted += 1

    con.commit()
    n = con.execute('SELECT COUNT(*) FROM life_snippet').fetchone()[0]
    print(f'phase10_local_life: inserted {inserted}; total snippets={n}')
    con.close()


if __name__ == '__main__':
    main()
