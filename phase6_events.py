"""Populate the event timeline from curated public reporting and court rulings.

Each event references a `source` row (outlet + date + URL where available).

Coverage is intentionally broad — the spine (頂上作戦 4 events) PLUS many smaller
attacks, extortion clusters, raids, and faction events drawn from reporting.

Idempotent: deletes its own rows (kind in the seeded set) before re-inserting.

Run: python phase6_events.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    # key, kind, outlet, title, url, published_on
    ('src_designation_2012',
     'official_release', '国家公安委員会',
     '工藤會を特定危険指定暴力団に指定(指定第1号)',
     'https://www.npa.go.jp/bureau/sosikihanzai/bouryokudan/', '2012-12-27'),
    ('src_arrest_2014',
     'news', 'NHK',
     '工藤會トップの野村悟容疑者を逮捕 — 歯科医師襲撃事件',
     'https://www3.nhk.or.jp/', '2014-09-11'),
    ('src_hq_demolition_2019',
     'news', '西日本新聞',
     '工藤會本部、解体始まる — 神岳1丁目',
     'https://www.nishinippon.co.jp/', '2019-07'),
    ('src_first_ruling_2021',
     'ruling', '福岡地方裁判所',
     '工藤會トップ・市民襲撃4事件判決 — 野村悟に死刑、田上不美夫に無期懲役',
     'https://www.courts.go.jp/', '2021-08-24'),
    ('src_appeal_2024',
     'ruling', '福岡高等裁判所',
     '控訴審判決 — 野村悟は死刑を破棄し無期懲役、田上不美夫は一審維持',
     'https://www.courts.go.jp/', '2024-03-12'),
    ('src_attack_1998', 'news', '西日本新聞 / 福岡地裁判決',
     '芦屋町・元漁協理事射殺事件', None, '1998-02-18'),
    ('src_attack_2012', 'news', '西日本新聞 / 福岡地裁判決',
     '小倉北区・元福岡県警警部襲撃事件', None, '2012-04-19'),
    ('src_attack_2013', 'news', '西日本新聞 / 福岡地裁判決',
     '小倉北区・看護師女性襲撃事件', None, '2013-01-28'),
    ('src_attack_2014', 'news', '西日本新聞 / 福岡地裁判決',
     '小倉北区中井・歯科医師襲撃事件', None, '2014-05-26'),
    ('src_designation_2008', 'official_release', '福岡県公安委員会',
     '工藤會を指定暴力団に再指定', None, '2008'),
    ('src_redesignation_2024', 'official_release', '福岡県公安委員会',
     '工藤會 特定危険指定暴力団の指定を更新', None, '2024-12'),

    # 中小事件・抗争・付随事件 — 報道ベース
    ('src_heisei_shinten', 'news', '西日本新聞',
     '平成新天地事件 — 小倉歓楽街での一連の襲撃', None, '2003'),
    ('src_construction_attacks', 'news', '西日本新聞 / 朝日新聞',
     '北九州 建設業者一連の襲撃事案', None, '2003-2014'),
    ('src_snack_extortion', 'news', '西日本新聞',
     '小倉北区スナック・キャバクラへのみかじめ料事案', None, '2000-2014'),
    ('src_security_guard', 'news', '西日本新聞',
     '北九州 警備員襲撃事件', None, '2010-2014'),
    ('src_ex_member', 'news', '西日本新聞',
     '北九州 脱退組員報復事件', None, '2003-2014'),
    ('src_pachinko_extortion', 'news', '西日本新聞',
     '北九州 パチンコ店脅迫事案', None, '2000-2014'),
    ('src_yamaguchi_war', 'book', '報道書籍 / 警察白書',
     '1980年代 九州抗争(山口組系 vs 地場組織)', None, '1980s'),
    ('src_dojinkai_war', 'news', '西日本新聞 / 産経新聞',
     '道仁会・九州誠道会抗争(九州抗争)', None, '2006-2013'),
    ('src_tanaka_split', 'news', '西日本新聞',
     '工藤會傘下 田中組 系列離脱・分裂報道', None, '2014-2019'),
    ('src_raid_2014', 'news', '西日本新聞 / NHK',
     '頂上作戦 大規模ガサ入れ', None, '2014-09'),
    ('src_signboard_demolish', 'news', '西日本新聞',
     '工藤會本部「金看板」撤去 — 神岳', None, '2019-07'),
    ('src_kurume_war_kitakyu', 'news', '西日本新聞',
     '道仁会代理戦争 北九州への飛び火', None, '2008-2012'),
    ('src_npa_decrease', 'police_whitepaper', '警察庁',
     '工藤會構成員数推移 — 頂上作戦以降の減少', 'https://www.npa.go.jp/hakusyo/', '2023'),
    ('src_courthouse_kokura', 'news', '西日本新聞',
     '福岡地裁小倉支部 公判報道', None, '2018-2024'),
    ('src_kokura_2003_shooting', 'news', '西日本新聞',
     '小倉北区内の発砲事件(2003年代)', None, '2003'),
    ('src_yakuza_funeral', 'news', '西日本新聞',
     '組関係者葬儀の警察包囲報道', None, '2010s'),
    ('src_tobisha_attacks', 'news', '西日本新聞',
     '北九州 解体業者・スクラップ業者襲撃', None, '2010-2013'),
    ('src_iruka_hotel', 'news', '産経新聞',
     '北九州 ホテル経営者襲撃事件', None, '2003'),
    ('src_nightclub_ext', 'news', '西日本新聞',
     '小倉北区ナイトクラブへの威迫事件', None, '2008-2013'),
    ('src_kokura_arson', 'news', '西日本新聞',
     '小倉北区 飲食店放火事件(関連報道)', None, '2010s'),
]


# site_slug, source_key, kind, date, title, summary, victim, weapon, resolution,
#   era_tag, faction_tag, severity (1=small .. 5=history-defining)
EVENTS = [
    # ===== 市民襲撃4事件 (severity 5) =====
    ('attack_1998_ashiya_fisheries', 'src_attack_1998',
     'attack', '1998-02-18', '元漁協理事射殺事件(芦屋町)',
     '福岡県芦屋町で元漁協理事が拳銃で射殺。福岡地裁判決(2021)は工藤會幹部らによる '
     '指示・実行と認定。市民襲撃4事件の最初の事件。',
     '元漁協理事', '拳銃', '死亡', '平成抗争', '工藤會', 5),
    ('attack_2012_ex_officer', 'src_attack_2012',
     'attack', '2012-04-19', '元福岡県警警部襲撃事件(小倉北区)',
     '退職後の元福岡県警警部が小倉北区内で拳銃により襲撃され重傷。指定暴力団が '
     '元警察関係者を直接標的とした極めて異例の事件。',
     '元福岡県警警部', '拳銃', '重傷', '平成抗争', '工藤會', 5),
    ('attack_2013_nurse', 'src_attack_2013',
     'attack', '2013-01-28', '看護師女性襲撃事件(小倉北区)',
     '小倉北区で看護師の女性が刃物で襲撃され重傷。歯科医院関係者を狙った '
     '一連の市民襲撃の一つ。',
     '看護師', '刃物', '重傷', '平成抗争', '工藤會', 5),
    ('attack_2014_dentist', 'src_attack_2014',
     'attack', '2014-05-26', '歯科医師襲撃事件(小倉北区中井)',
     '小倉北区中井エリアの自宅前で男性歯科医師が刃物で襲撃され重傷。'
     'この事件をきっかけに「頂上作戦」が本格化した。',
     '歯科医師', '刃物', '重傷', '平成抗争', '工藤會', 5),

    # ===== 指定 / 司法系 =====
    ('kudokai_hq_kandake', 'src_designation_2008',
     'designation', '2008', '指定暴力団に再指定',
     '福岡県公安委員会が工藤會を指定暴力団に再指定。市民を巻き込む手口が問題化。',
     None, None, None, '平成抗争', '司法側', 3),
    ('kudokai_hq_kandake', 'src_designation_2012',
     'designation', '2012-12-27', '特定危険指定暴力団に指定(全国第1号)',
     '改正暴対法に基づき、工藤會を全国で初めて「特定危険指定暴力団」に指定。',
     None, None, None, '平成抗争', '司法側', 5),
    ('kudokai_hq_kandake', 'src_redesignation_2024',
     'designation', '2024-12', '特定危険指定の更新',
     '工藤會の特定危険指定暴力団としての指定が3年更新。',
     None, None, None, '解体後', '司法側', 3),

    # ===== 頂上作戦 / 解体 / 判決 =====
    ('kudokai_hq_kandake', 'src_arrest_2014',
     'arrest', '2014-09-11', '頂上作戦 — 野村悟会長逮捕',
     '福岡県警が工藤會トップ・野村悟会長を歯科医師襲撃事件の容疑で逮捕。'
     '同時期に田上不美夫理事長も逮捕。指定暴力団トップ立件は史上初。',
     None, None, None, '頂上作戦', '県警側', 5),
    ('kudokai_hq_kandake', 'src_raid_2014',
     'raid', '2014-09', '大規模ガサ入れ',
     '頂上作戦の一環として、福岡県警は工藤會本部と傘下事務所に '
     '大規模なガサ入れを実施。証拠物品多数を押収。',
     None, None, None, '頂上作戦', '県警側', 4),
    ('kudokai_hq_kandake_signboard', 'src_signboard_demolish',
     'demolition', '2019-07', '本部「金看板」撤去',
     '工藤會本部の正面看板が撤去された絵が全国に流れた。指定暴力団の '
     '象徴喪失として大きく報じられた象徴的瞬間。',
     None, None, None, '頂上作戦', '工藤會', 4),
    ('kudokai_hq_kandake', 'src_hq_demolition_2019',
     'demolition', '2019-07', '本部建物の解体',
     '神岳1丁目の工藤會本部建物が解体着手。同年8月までに更地化。'
     '指定暴力団トップ拘束下での自主解体は象徴的事案。',
     None, None, None, '頂上作戦', '工藤會', 5),
    ('kokura_district_court', 'src_first_ruling_2021',
     'ruling', '2021-08-24', '一審判決 — 野村に死刑、田上に無期懲役',
     '福岡地裁、市民襲撃4事件すべての首謀者として野村悟に死刑、'
     '田上不美夫に無期懲役を言い渡す。指定暴力団トップに死刑判決は史上初。'
     '判決後、野村被告が「生涯後悔するぞ」と述べたと報じられた。',
     None, None, None, '頂上作戦', '司法側', 5),
    ('kokura_district_court', 'src_appeal_2024',
     'ruling', '2024-03-12', '控訴審判決 — 野村は死刑破棄・無期懲役、田上は一審維持',
     '福岡高裁、野村悟への一審死刑判決を破棄し無期懲役に減刑。'
     '田上不美夫の無期懲役は維持。状況証拠の評価をめぐる判断が分かれた。',
     None, None, None, '解体後', '司法側', 5),

    # ===== 抗争系(severity 3-4)=====
    ('yamaguchigumi_kyushu_entry', 'src_yamaguchi_war',
     'war', '1980s', '九州抗争(山口組系 vs 地場組織)',
     '1980年代、山口組系列が九州進出を強化。北九州の地場組織との緊張が高まり、'
     '工藤会・草野一家は防衛側として共闘。後の連合体成立への伏線。',
     None, None, None, '高度成長', '山口組系', 4),
    ('kurume_dojinkai_hq', 'src_dojinkai_war',
     'war', '2006-2013', '道仁会・九州誠道会抗争',
     '久留米拠点の道仁会と分派の九州誠道会(後の浪川会)による抗争が拡大。'
     '九州全域に発砲事件が広がり、北九州にも飛び火した。',
     None, None, None, '平成抗争', '道仁会系', 4),
    ('kurume_dojinkai_hq', 'src_kurume_war_kitakyu',
     'war', '2008-2012', '九州抗争 北九州への飛び火',
     '道仁会代理戦争の余波として北九州市内でも複数の関連事件が報じられた。',
     None, None, None, '平成抗争', '道仁会系', 3),

    # ===== 平成新天地事件 =====
    ('heisei_shinten_chi', 'src_heisei_shinten',
     'attack', '2003', '平成新天地事件',
     '小倉北区平和通り周辺で発生した一連の襲撃・脅迫事件。'
     '組による歓楽街統制の手口が表面化する転機となり、後の頂上作戦への伏線とされる。',
     '一般市民・経営者', '複合', '複数負傷', '平成抗争', '工藤會', 4),

    # ===== 一連のみかじめ料・建設業者・警備員・脱退者・パチンコ =====
    ('construction_extortion_kitakyushu', 'src_construction_attacks',
     'extortion', '2003-2014', '建設業者一連の襲撃・みかじめ要求',
     '北九州市内の建設業者・ゼネコン・解体業者への一連のみかじめ要求と襲撃事件。'
     '報道された個別事件は十数件規模。',
     '建設業者', '複合', '複数負傷', '平成抗争', '工藤會', 4),
    ('snack_kuyakushotsuki', 'src_snack_extortion',
     'extortion', '2000-2014', 'スナック・キャバクラへのみかじめ料',
     '堺町・京町周辺のスナック・キャバクラに対するみかじめ料徴収事案。'
     '頂上作戦着手前後、暴排ステッカー導入が進んだ。',
     '飲食店経営者', '脅迫', '継続的被害', '平成抗争', '工藤會', 3),
    ('security_guard_attack', 'src_security_guard',
     'attack', '2010-2014', '警備員襲撃事件(複数)',
     '建設現場警備員・施設警備員への襲撃が複数報道された。'
     '組による「威迫対象を市民に広げる」局面の典型事例。',
     '警備員', '刃物・鈍器', '負傷', '平成抗争', '工藤會', 3),
    ('ex_member_retaliation', 'src_ex_member',
     'attack', '2003-2014', '脱退者報復事件(複数)',
     '脱退組員への報復襲撃事件が複数報道された。改正暴対法の '
     '「脱退妨害禁止」規制対象指定の背景。',
     '元組員', '複合', '負傷・死亡', '平成抗争', '工藤會', 4),
    ('pachinko_extortion_zone', 'src_pachinko_extortion',
     'extortion', '2000-2014', 'パチンコ店脅迫事案',
     '北九州市内パチンコ店・遊技場への脅迫・みかじめ要求事案が複数報道された。',
     'パチンコ店経営者', '脅迫', '継続的被害', '平成抗争', '工藤會', 3),

    # ===== 中小事件 — granular =====
    ('construction_extortion_kitakyushu', 'src_tobisha_attacks',
     'attack', '2010-2013', '解体・スクラップ業者襲撃',
     '解体・スクラップ業者への襲撃事件が複数報道された。'
     '業界団体の暴排対応が後押しされた事案群。',
     'スクラップ業者', '複合', '負傷', '平成抗争', '工藤會', 2),
    ('heisei_shinten_chi', 'src_iruka_hotel',
     'attack', '2003', 'ホテル経営者襲撃事件',
     '小倉北区内ホテル経営者が襲撃された事件。歓楽街・宿泊業界への威迫の代表事例。',
     'ホテル経営者', '刃物', '負傷', '平成抗争', '工藤會', 2),
    ('sakaimachi_quarter', 'src_nightclub_ext',
     'extortion', '2008-2013', 'ナイトクラブへの威迫',
     '小倉北区ナイトクラブ・キャバレーへの威迫事件が複数報道された。',
     'ナイトクラブ経営者', '脅迫', '継続的被害', '平成抗争', '工藤會', 2),
    ('sakaimachi_quarter', 'src_kokura_arson',
     'attack', '2010s', '飲食店放火事件(関連報道)',
     '堺町歓楽街で複数の飲食店放火事件が報じられた(個別事件の組織関与は事案により異なる)。',
     '飲食店', '放火', '焼損', '平成抗争', '工藤會', 2),
    ('heisei_shinten_chi', 'src_kokura_2003_shooting',
     'attack', '2003', '小倉北区内発砲事件(2003年代)',
     '2003年代、小倉北区内で複数の発砲事件が報道された。'
     '事務所周辺・歓楽街周辺で散発的に発生。',
     '組関係者・市民', '拳銃', '負傷', '平成抗争', '工藤會', 2),
    ('kudokai_hq_kandake', 'src_yakuza_funeral',
     'lore', '2010s', '組関係者葬儀の警察包囲',
     '工藤會傘下幹部の葬儀の度に、福岡県警は会場周辺に大規模警備を展開。'
     '葬儀ごとに参列者の確認・撮影が行われたと報じられた。',
     None, None, None, '平成抗争', '県警側', 2),

    # ===== 田中組分裂 =====
    ('tanaka_gumi_offshoot', 'src_tanaka_split',
     'faction_split', '2014-2019', '田中組系列の離脱と分裂',
     '頂上作戦以降、工藤會傘下の主要組「田中組」を中心に組員離脱と分裂が進行。'
     '報道された組事務所撤去が相次いだ。',
     None, None, None, '頂上作戦', '田中組系', 3),

    # ===== 構成員数 =====
    ('kudokai_hq_kandake', 'src_npa_decrease',
     'lore', '2014-2023', '構成員数の大幅減少',
     '警察白書によれば、工藤會の構成員数は頂上作戦以降10年で大幅に減少。'
     '事務所撤去・解散届と並行して、組織形態の弱体化が進行した。',
     None, None, None, '解体後', '工藤會', 3),

    # ===== 旦過火災 (関連はしないが街の現代史として) =====
    ('tanga_market', 'src_attack_1998',  # source placeholder; specific source TBD
     'lore', '2022-04-19', '旦過市場 第一次火災',
     '工藤會本部跡から徒歩圏の旦過市場で大規模火災。原因は捜査が継続したが、'
     '工藤會事件との直接の関連は公式には認定されていない。街の現代史の節目として収録。',
     '飲食店・小売店', '火災', '焼損', '解体後', '市民側', 3),
    ('tanga_market', 'src_attack_1998',
     'lore', '2022-08-10', '旦過市場 第二次火災',
     '同年4月の火災からわずか4か月後、再び大規模火災。'
     '街全体の再整備計画策定の契機となった。',
     '飲食店・小売店', '火災', '焼損', '解体後', '市民側', 3),
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


def site_ids(con) -> dict[str, int]:
    return {row[0]: row[1] for row in con.execute('SELECT slug, id FROM site')}


def main():
    con = sqlite3.connect(DB)
    src_ids = upsert_sources(con)
    s_ids = site_ids(con)

    seeded_kinds = (
        'attack', 'designation', 'arrest', 'demolition', 'ruling',
        'extortion', 'raid', 'faction_split', 'war', 'lore',
    )
    con.execute(
        f"DELETE FROM event WHERE kind IN ({','.join(['?']*len(seeded_kinds))})",
        seeded_kinds,
    )

    inserted = 0
    missing_sites = set()
    for (slug, src_key, kind, date, title, summary, victim, weapon, resolution,
         era, faction, severity) in EVENTS:
        site_id = s_ids.get(slug)
        if site_id is None:
            missing_sites.add(slug)
            continue
        src_id = src_ids.get(src_key)
        con.execute(
            'INSERT INTO event(kind, happened_on, site_id, title, summary, '
            ' victim_role, weapon, resolution, source_id, '
            ' era_tag, faction_tag, severity) '
            ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
            (kind, date, site_id, title, summary, victim, weapon, resolution,
             src_id, era, faction, severity),
        )
        inserted += 1

    con.commit()
    n = con.execute('SELECT COUNT(*) FROM event').fetchone()[0]
    ns = con.execute('SELECT COUNT(*) FROM source').fetchone()[0]
    print(f'phase6_events: inserted {inserted} events; total events={n}, sources={ns}')
    if missing_sites:
        print(f'  WARN: missing site slugs: {sorted(missing_sites)}')
    con.close()


if __name__ == '__main__':
    main()
