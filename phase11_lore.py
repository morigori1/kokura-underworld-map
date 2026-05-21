"""Phase 11: lore — colorful, entertainment-leaning anecdotes from public reporting.

These rows go in the `lore` table and render as a separate, gold-trimmed card
style in the dashboard. They're sourced from public reporting (西日本新聞・産経・
共同・朝日・毎日 ほか)+ 警察白書 + 報道書籍 and include the kind of
character-and-flavor detail that traditional OSINT layers strip out.

spice 1-5: 1 = mild context, 5 = legendary anecdote.

Idempotent. Run: python phase11_lore.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    # key, kind, outlet, title, url, published_on
    ('lor_nomura_courtroom', 'news', '西日本新聞 / 共同通信',
     '野村悟・判決言渡時の在廷発言報道(2021-08-24)', None, '2021-08-24'),
    ('lor_kanban', 'news', '西日本新聞 / NHK',
     '工藤會本部「金看板」撤去の絵', None, '2019-07'),
    ('lor_kusano_takaaki', 'book', '報道書籍 / 西日本新聞',
     '初代総長 草野高明の戦後闇市出自と人物像', None, '2000s'),
    ('lor_kudo_genji', 'book', '報道書籍',
     '初代組長 工藤玄治と中津・北九州ライン', None, '2000s'),
    ('lor_yamaguchi_kyushu', 'book', '報道書籍 / 警察白書',
     '1980年代 山口組九州進出と地場連合の防衛', None, '1980s'),
    ('lor_dojin_kyushu_war', 'news', '西日本新聞 / 産経新聞',
     '道仁会・誠道会(浪川会)抗争 — 北九州への余波', None, '2006-2013'),
    ('lor_funeral_cordon', 'news', '西日本新聞',
     '組関係者葬儀の警察包囲・身元確認報道', None, '2010s'),
    ('lor_heisei_shinten', 'news', '西日本新聞 / 産経新聞',
     '平成新天地事件報道', None, '2003'),
    ('lor_kane_kanban_origin', 'news', '西日本新聞',
     '「金看板」の通称の由来報道', None, '1990s-2010s'),
    ('lor_tanaka_gumi_split', 'news', '西日本新聞',
     '田中組分裂・組事務所撤去報道', None, '2014-2019'),
    ('lor_kuyakushotsuki', 'news', '西日本新聞',
     '堺町・京町歓楽街の暴排ステッカー導入', None, '2010s'),
    ('lor_takeda_kosaku', 'news', '西日本新聞 / 朝日新聞',
     '頂上作戦の指揮 — 福岡県警組織犯罪対策課', None, '2014'),
    ('lor_tobi_attack', 'news', '西日本新聞',
     '解体・スクラップ業者襲撃報道', None, '2010-2013'),
    ('lor_kudokai_dress', 'news', '西日本新聞',
     '工藤會幹部の出廷時服装報道', None, '2018-2021'),
    ('lor_kokura_keisatsu_kindistance', 'news', '西日本新聞',
     '工藤會本部と小倉北警察署の近接立地について', None, '2010s'),
    ('lor_npa_decrease', 'police_whitepaper', '警察庁',
     '工藤會構成員数推移 — 警察白書', 'https://www.npa.go.jp/hakusyo/', '2023'),
    ('lor_uomachi_genealogy', 'book', '北九州市史 / 商店街振興組合',
     '魚町銀天街と戦後闇市文化の系譜', None, '1990s-'),
    ('lor_dentist_after', 'news', '西日本新聞',
     '歯科医師襲撃事件 被害者の闘病報道', None, '2014-2021'),
    ('lor_courthouse_security', 'news', '西日本新聞',
     '福岡地裁小倉支部の公判時警備', None, '2018-2024'),
    ('lor_kyumeido_disband', 'news', '西日本新聞',
     '九州誠道会の解散と再編', None, '2013'),
]


# ord, site_slug (or None), year_label, title, body, spice, era_tag, faction_tag, source_key
LORE = [
    (10, 'kusano_ikka_origin_kokura', '1947',
     '草野高明 — 戦後小倉の闇市から',
     '初代総長 草野高明は戦後の小倉でテキ屋系から身を起こした。'
     '小倉駅・旦過市場周辺の闇市の延長に、地場のショバ取りと祭りの仕切りが '
     'あった時代の人物として報道書籍に繰り返し描かれている。'
     '北九州の戦後街区の「もうひとつの統治者」だった、と評する記事もある。',
     4, '戦後闇市', '草野一家系', 'lor_kusano_takaaki'),

    (20, 'kudogumi_nakatsu_origin', '1953',
     '工藤玄治 — 大分・中津から北九州ラインへ',
     '初代組長 工藤玄治が大分県中津市で工藤組を結成。'
     '関門海峡を跨ぐ「中津 ⇄ 門司 ⇄ 小倉」ラインが '
     '後の工藤連合草野一家成立の地理的基盤になったと報道書籍は整理する。',
     3, '戦後闇市', '工藤組系', 'lor_kudo_genji'),

    (30, 'ogura_keisatsu', '1980s-2010s',
     '神岳の「金看板」と小倉北警察署が徒歩2分',
     '工藤會本部の正面看板(通称「金看板」)から小倉北警察署までは、地図上で約200m。'
     'この「本部と警察署が至近距離」という構図は、戦後北九州の独特な統治構造を '
     '象徴する絵として、多くのドキュメンタリーに繰り返し映された。',
     5, '高度成長', '工藤會', 'lor_kokura_keisatsu_kindistance'),

    (40, 'yamaguchigumi_kyushu_entry', '1980s',
     '山口組九州進出と地場の防衛戦',
     '1980年代、山口組系列が九州に勢力を伸ばし、北九州の地場組織との間に '
     '緊張が生まれた。工藤会と草野一家は防衛側として共闘姿勢を強め、'
     '1987年の「工藤連合草野一家」成立はこの圧力下の合体と位置づけられる。'
     '当時の関門海峡は組関係者の往来監視ラインだった、と語る報道もある。',
     4, '高度成長', '山口組系', 'lor_yamaguchi_kyushu'),

    (50, 'kudokai_hq_kandake', '2000',
     '工藤會改称と「会長制」への移行',
     '2000年、組織名を「工藤會」に統一。野村悟が会長に就任し、'
     '三代目総裁制から会長制へ移行した。北九州の地場連合体が「会」を名乗る '
     '大規模組織として整流された節目。',
     2, '平成抗争', '工藤會', None),

    (60, 'heisei_shinten_chi', '2003',
     '「平成新天地事件」— 歓楽街で何が起きたか',
     '小倉北区平和通り周辺の歓楽街で発生した一連の襲撃・脅迫事件。'
     '報道当時は、組による歓楽街統制の手口がはじめて全国版で「事件名」として '
     '括られた象徴的事案。後に、これが市民威迫の手口の本格化と整理される。',
     4, '平成抗争', '工藤會', 'lor_heisei_shinten'),

    (70, 'kurume_dojinkai_hq', '2006-2013',
     '道仁会・九州誠道会の代理戦争(北九州にも飛び火)',
     '久留米拠点の道仁会と分派の九州誠道会(後の浪川会)による抗争は '
     '九州全域に拡大。発砲事件が市街地で頻発し、巻き添えへの懸念から '
     '福岡県警は特別警戒を組み続けた。北九州の工藤會縄張りにも余波が及び、'
     '地場連合体としての一体化を促した側面がある。',
     4, '平成抗争', '道仁会系', 'lor_dojin_kyushu_war'),

    (75, 'kurume_dojinkai_hq', '2013',
     '九州誠道会の解散と浪川会への再編',
     '長引いた抗争の終結局面として、九州誠道会は2013年に解散届を提出。'
     'その後、浪川会として再編。北九州への直接の余波は減少したが、'
     '工藤會の縄張り問題に与えた影響は無視できない、と整理される。',
     3, '平成抗争', '道仁会系', 'lor_kyumeido_disband'),

    (80, 'attack_2014_dentist', '2014-05-26',
     '歯科医師襲撃事件 — 「頂上作戦」の引き金',
     '2014年5月、小倉北区中井の自宅前で男性歯科医師が刃物で襲撃された。'
     '報道は「県警の堪忍袋の緒が切れた」と表現し、3か月後の9月、'
     '会長・理事長を相次いで逮捕する頂上作戦が始動した。',
     5, '頂上作戦', '工藤會', 'lor_dentist_after'),

    (85, 'fukuoka_kenkei', '2014-09',
     '頂上作戦 — 県警組織犯罪対策課の指揮',
     '頂上作戦は福岡県警の組織犯罪対策課を中心に、本部・小倉北署・関係署が '
     '一体で展開した大規模捜査。報道は「捜査員数百人規模のガサ」と伝えた。',
     4, '頂上作戦', '県警側', 'lor_takeda_kosaku'),

    (90, 'tanaka_gumi_offshoot', '2014-2019',
     '田中組の解体・組事務所撤去ラッシュ',
     '頂上作戦以降、工藤會傘下の主要組「田中組」を中心に組員離脱・分裂が進行。'
     '組事務所の撤去報道が相次ぎ、北九州各地で「組事務所跡」の絵が新聞紙面に並んだ。',
     3, '頂上作戦', '田中組系', 'lor_tanaka_gumi_split'),

    (100, 'sakaimachi_quarter', '2010s',
     '堺町歓楽街の暴排ステッカー',
     '頂上作戦以降、堺町・京町の飲食店店頭に「暴力団排除」ステッカーが急速に普及。'
     '一枚一枚は小さい絵だが、「街の側が拒否する」可視化の積み重ねとして '
     '報道された。',
     2, '頂上作戦', '市民側', 'lor_kuyakushotsuki'),

    (110, 'kudokai_hq_kandake_signboard', '2019-07',
     '「金看板」の撤去',
     '工藤會本部の正面に長年掲げられていた金属製看板。'
     '解体時、クレーンで吊り下げられる絵が全国に流れた。'
     '「指定暴力団の看板を撤去する」象徴的瞬間として、複数の媒体が一面写真で報じた。',
     5, '頂上作戦', '工藤會', 'lor_kanban'),

    (115, 'kudokai_hq_kandake_signboard', '1990s-2010s',
     '「金看板」の通称の由来',
     '神岳の本部看板は表面処理から「金属の輝き」「組の格を示す金看板」など '
     '呼称が混在した。報道書籍には「絵柄ではなく存在そのものが象徴だった」と '
     '評する記述が残る。',
     3, '高度成長', '工藤會', 'lor_kane_kanban_origin'),

    (120, 'kudokai_hq_kandake', '2010s',
     '組関係者葬儀の警察包囲',
     '工藤會傘下幹部の葬儀の度に、福岡県警は会場周辺に大規模警備を展開した。'
     '参列者の確認・撮影が常態化し、葬儀という私的行事に '
     '公権力が並ぶ絵が繰り返された。',
     3, '平成抗争', '県警側', 'lor_funeral_cordon'),

    (130, 'kokura_district_court', '2018-2021',
     '工藤會幹部の出廷時服装',
     '頂上作戦後の公判では、被告らの出廷時の服装(スーツ・ノーネクタイなど)が '
     '報道写真の定番となった。連日傍聴席が満員になる公判もあった。',
     2, '頂上作戦', '司法側', 'lor_kudokai_dress'),

    (140, 'kokura_district_court', '2021-08-24',
     '「生涯後悔するぞ」— 法廷内発言報道',
     '一審の死刑判決言渡時、野村悟被告が裁判官に向かって「生涯後悔するぞ」と '
     '述べたとされる発言が複数の媒体に報じられた。'
     '指定暴力団トップへの死刑判決という史上初の場面の象徴シーンとなった。',
     5, '頂上作戦', '工藤會', 'lor_nomura_courtroom'),

    (145, 'kokura_district_court', '2018-2024',
     '小倉支部の公判時警備',
     '工藤會関連の公判が開かれる日の福岡地裁小倉支部は、'
     '入口の金属探知・周辺道路の警備強化・傍聴券抽選の長蛇列など、'
     '地方裁判所としては異例の警備態勢が常態化した。',
     2, '頂上作戦', '司法側', 'lor_courthouse_security'),

    (150, 'kudokai_hq_kandake', '2014-2023',
     '構成員数の大幅減少 — 警察白書から',
     '警察白書によれば、工藤會の構成員数は頂上作戦以降10年で大幅に減少。'
     '事務所撤去・解散届と並行して、組織形態の弱体化が進行した。',
     3, '解体後', '工藤會', 'lor_npa_decrease'),

    (160, 'uomachi_arcade', '1951-',
     '魚町銀天街 — 闇市から日本初のアーケードへ',
     '魚町銀天街は1951年に完成した日本初の本格的アーケード商店街。'
     '草野一家発祥期の闇市文化と同じ街区にあり、'
     '「合法側の街の動脈」と「もうひとつの統治」が並走した北九州の二重構造の片側。',
     3, '戦後闇市', '市民側', 'lor_uomachi_genealogy'),

    (170, 'construction_extortion_kitakyushu', '2010-2013',
     '解体・スクラップ業者襲撃の集中',
     'リーマンショック後の鉄スクラップ価格高騰期、工藤會系による解体・'
     'スクラップ業者への襲撃事件が集中して報じられた。'
     '当時の業界状況と組のショバ取りの動きが連動した事案群。',
     3, '平成抗争', '工藤會', 'lor_tobi_attack'),
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
    s_ids = {row[0]: row[1] for row in cur.execute('SELECT slug, id FROM site')}
    src_ids = upsert_sources(con)

    cur.execute('DELETE FROM lore')

    inserted = 0
    missing = []
    for (ord_, slug, year, title, body, spice, era, faction, src_key) in LORE:
        site_id = s_ids.get(slug) if slug else None
        if slug and site_id is None:
            missing.append(slug)
        src_id = src_ids.get(src_key) if src_key else None
        cur.execute(
            'INSERT INTO lore(ord, site_id, year_label, title, body, spice, '
            ' era_tag, faction_tag, source_id) VALUES (?,?,?,?,?,?,?,?,?)',
            (ord_, site_id, year, title, body, spice, era, faction, src_id),
        )
        inserted += 1

    con.commit()
    print(f'phase11_lore: inserted {inserted} lore entries')
    if missing:
        print(f'  WARN: missing slugs: {sorted(set(missing))}')
    con.close()


if __name__ == '__main__':
    main()
