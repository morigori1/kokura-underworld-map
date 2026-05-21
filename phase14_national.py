"""Phase 14: national yakuza context for positioning Kudo-kai.

Events that don't happen in Kokura but shape Kudo-kai's environment:
  - 三代目山口組分裂 → 一和会創設 → 山一抗争 (1985-1989)
  - 暴対法成立(1991)・施行(1992)・累次の改正
  - 六代目山口組成立 → 神戸山口組分裂(2015)→ 任侠山口組 → 絆會
  - 山口組系の特定抗争指定暴力団指定(2020-2023)
  - 九州抗争(道仁会・九州誠道会) 詳細
  - 暴排条例の全国整備

Anchors to existing context sites (国会・山口組進出ライン・道仁会拠点 など).

Idempotent. Run: python phase14_national.py
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('nat_yamaichi_war', 'news', '読売新聞 / 朝日新聞',
     '三代目山口組分裂・山一抗争関連報道(1984-1989)', None, '1985-1989'),
    ('nat_yamaichi_book', 'book', '山平重樹ほか',
     '報道書籍『山一抗争』ほか — 1985年分裂から抗争終結まで', None, '1990s'),
    ('nat_bouhouhou_seiritsu', 'legislative_record', '衆議院 / 参議院',
     '暴対法成立 — 1991年第120回国会', 'https://kokkai.ndl.go.jp/', '1991-05-15'),
    ('nat_bouhouhou_shikou', 'official_release', '警察庁',
     '暴対法施行 — 1992-03-01', 'https://www.npa.go.jp/', '1992-03-01'),
    ('nat_bouhouhou_kaisei2008', 'legislative_record', '衆議院 / 参議院',
     '暴対法改正(2008) — 事務所使用制限の強化', 'https://kokkai.ndl.go.jp/', '2008'),
    ('nat_bouhouhou_kaisei2012', 'legislative_record', '衆議院 / 参議院',
     '暴対法改正(2012) — 特定危険指定の新設', 'https://kokkai.ndl.go.jp/', '2012-10-30'),
    ('nat_6rokudaime', 'news', '朝日新聞',
     '六代目山口組成立(2005)', None, '2005-07'),
    ('nat_kobe_split', 'news', '朝日新聞 / 共同通信',
     '神戸山口組分裂(2015-08-27)', None, '2015-08-27'),
    ('nat_ninkyo_split', 'news', '朝日新聞',
     '任侠山口組分裂(2017-04)', None, '2017-04'),
    ('nat_kizuna_rename', 'news', '朝日新聞',
     '任侠山口組から「絆會」へ改称', None, '2020-01'),
    ('nat_tokutei_kousou', 'official_release', '国家公安委員会',
     '六代目山口組・神戸山口組を特定抗争指定暴力団に指定(2020-01)',
     'https://www.npa.go.jp/', '2020-01-07'),
    ('nat_tokutei_kousou_end', 'official_release', '国家公安委員会',
     '特定抗争指定暴力団 指定解除(段階的・2023-)',
     'https://www.npa.go.jp/', '2023-04'),
    ('nat_kyushu_kossou_full', 'news', '西日本新聞 / 産経新聞 / 共同通信',
     '九州抗争(道仁会・九州誠道会)— 全国紙連続報道', None, '2006-2013'),
    ('nat_bouhai_jorei', 'official_release', '全国都道府県',
     '暴力団排除条例の全国整備(2010-2011)', None, '2010-2011'),
    ('nat_fukushima_pref', 'official_release', '福岡県',
     '福岡県暴力団排除条例 施行(2010-04-01)',
     'https://www.pref.fukuoka.lg.jp/', '2010-04-01'),
    ('nat_npa_white_full', 'police_whitepaper', '警察庁',
     '警察白書 暴力団情勢の年次推移(2010-2024)',
     'https://www.npa.go.jp/hakusyo/', '2010-2024'),
    ('nat_yamaguchigumi_breakup_book', 'book', '溝口敦 ほか',
     '六代目山口組分裂と神戸山口組創設 関連書籍', None, '2015-2018'),
    ('nat_taishu_kai_zoku', 'news', '西日本新聞',
     '太州会・福博会の動向(九州地場)', None, '2010s'),
    ('nat_ofac_2024_review', 'sanctions', 'U.S. Treasury OFAC',
     'OFAC TCO 指定の継続レビュー(2014-)', None, '2014-'),
    ('nat_state_dept_reward', 'sanctions', 'U.S. Department of State',
     'Rewards for Justice Program 関連 — TCO 情報提供報奨',
     'https://www.state.gov/rewards-for-justice/', '2013-'),
]


# site_slug, source_key, kind, date, title, summary, victim, weapon, resolution,
#   era_tag, faction_tag, severity
EVENTS = [
    # ===== 山口組系全国コンテキスト =====
    ('yamaguchigumi_kyushu_entry', 'nat_yamaichi_war',
     'war', '1985-08-27',
     '三代目山口組分裂・一和会創設',
     '1985年8月27日、三代目山口組から一部幹部が離脱して一和会を創設。'
     '直後から両組織の抗争(山一抗争)が全国規模で発生し、'
     '北九州の地場連合体形成の地政学的圧力背景となった。',
     None, '拳銃', None, '高度成長', '山口組系', 4),

    ('yamaguchigumi_kyushu_entry', 'nat_yamaichi_war',
     'war', '1989',
     '山一抗争終結',
     '4年余りに及んだ山口組と一和会の抗争が1989年に終結。'
     'この間、全国でおよそ300件以上の襲撃事件が報じられ、'
     '一般市民を巻き込む暴力団抗争の異常性が社会問題化した。'
     '後の暴対法成立(1991)の主要な背景の一つ。',
     None, '拳銃', None, '高度成長', '山口組系', 4),

    ('kokkai_diet_tokyo', 'nat_bouhouhou_seiritsu',
     'designation', '1991-05-15',
     '暴対法成立 — 暴力団員による不当な行為の防止等に関する法律',
     '第120回国会で「暴力団員による不当な行為の防止等に関する法律」(暴対法)が成立。'
     '指定暴力団制度を新設、不当要求行為を行政命令の対象に。'
     '工藤會を含む全国の主要組織が翌1992年から順次「指定暴力団」となる法的枠組み。',
     None, None, None, '高度成長', '司法側', 5),

    ('kokkai_diet_tokyo', 'nat_bouhouhou_shikou',
     'designation', '1992-03-01',
     '暴対法 施行',
     '1992年3月1日、暴対法が施行。同年の指定第1陣で山口組・住吉会・稲川会など '
     '主要組織が指定暴力団に。九州地場では工藤連合草野一家・道仁会などが対象に。',
     None, None, None, '高度成長', '司法側', 4),

    ('kokkai_diet_tokyo', 'nat_bouhouhou_kaisei2008',
     'designation', '2008',
     '暴対法改正(2008) — 事務所使用制限の強化',
     '暴対法改正により、指定暴力団事務所の周辺住民訴訟支援・使用制限規定が強化。'
     '工藤會を含む指定暴力団の事務所運営に直接の制約が及ぶようになった。',
     None, None, None, '平成抗争', '司法側', 3),

    ('kokkai_diet_tokyo', 'nat_bouhouhou_kaisei2012',
     'designation', '2012-10-30',
     '暴対法改正(2012) — 特定危険指定の新設',
     '改正暴対法が成立、「特定危険指定暴力団」「特定抗争指定暴力団」制度が新設。'
     '同年12月、工藤會が特定危険指定第1号となった。',
     None, None, None, '平成抗争', '司法側', 5),

    ('yamaguchigumi_kyushu_entry', 'nat_6rokudaime',
     'merger', '2005-07',
     '六代目山口組成立',
     '五代目から六代目への代替わり。司忍が六代目組長に就任。'
     '全国最大の指定暴力団としての体制が再編された節目。'
     '工藤會を含む地場連合体には組織形態的に変化なし。',
     None, None, None, '平成抗争', '山口組系', 3),

    ('yamaguchigumi_kyushu_entry', 'nat_kobe_split',
     'faction_split', '2015-08-27',
     '神戸山口組分裂',
     '六代目山口組から複数の二次団体が離脱し神戸山口組を結成。'
     '全国規模の組織犯罪情勢に影響。工藤會は地場連合体として中立を保ったが、'
     '九州内でも一部関係組の動きが報じられた。',
     None, None, None, '頂上作戦', '山口組系', 4),

    ('yamaguchigumi_kyushu_entry', 'nat_ninkyo_split',
     'faction_split', '2017-04',
     '任侠山口組分裂',
     '神戸山口組からさらに分派して任侠山口組(後に絆會)が成立。'
     '三派対立の構図が確立、全国の抗争圧力が高まる。',
     None, None, None, '頂上作戦', '山口組系', 3),

    ('yamaguchigumi_kyushu_entry', 'nat_kizuna_rename',
     'faction_split', '2020-01',
     '任侠山口組→絆會 改称',
     '任侠山口組が組織名を「絆會(きずなかい)」に変更。',
     None, None, None, '解体後', '山口組系', 2),

    ('yamaguchigumi_kyushu_entry', 'nat_tokutei_kousou',
     'designation', '2020-01-07',
     '六代目山口組・神戸山口組を特定抗争指定',
     '改正暴対法に基づき、六代目山口組と神戸山口組を「特定抗争指定暴力団」に指定。'
     '工藤會とは別カテゴリ(特定危険指定 vs 特定抗争指定)の対象としての並列存在。',
     None, None, None, '解体後', '司法側', 3),

    ('yamaguchigumi_kyushu_entry', 'nat_tokutei_kousou_end',
     'designation', '2023-04',
     '特定抗争指定 段階的解除',
     '抗争事件の沈静化を受け、特定抗争指定が段階的に解除へ。'
     '一方、工藤會の特定危険指定は別判断で更新が継続される。',
     None, None, None, '解体後', '司法側', 2),

    # ===== 九州抗争詳細 =====
    ('kurume_dojinkai_hq', 'nat_kyushu_kossou_full',
     'war', '2006',
     '九州抗争 始発 — 道仁会内紛',
     '久留米拠点の道仁会内で内紛が表面化、九州誠道会の独立分派につながる。'
     '以降6年にわたる九州規模の抗争(九州抗争)の起点。',
     None, None, None, '平成抗争', '道仁会系', 4),

    ('kurume_dojinkai_hq', 'nat_kyushu_kossou_full',
     'war', '2007-2012',
     '九州抗争 — 各地の発砲・襲撃',
     '九州抗争中、福岡・長崎・佐賀・大分などで発砲事件・襲撃事件が連続。'
     '一般市民の巻き添えへの懸念から各県警が特別警戒を組み続けた。'
     '北九州の工藤會縄張りにも一部余波が及んだ。',
     None, '拳銃', '複数死傷', '平成抗争', '道仁会系', 4),

    ('kurume_dojinkai_hq', 'nat_kyushu_kossou_full',
     'designation', '2012-12-27',
     '道仁会・九州誠道会を特定抗争指定',
     '工藤會の特定危険指定と同時期、道仁会と九州誠道会も特定抗争指定に。'
     '九州抗争の沈静化と暴対法改正の両軸での規制強化。',
     None, None, None, '平成抗争', '司法側', 4),

    # ===== 全国の暴排条例 =====
    ('fukuoka_pref_assembly', 'nat_fukushima_pref',
     'designation', '2010-04-01',
     '福岡県 暴力団排除条例 施行',
     '福岡県暴力団排除条例が施行。事業者の暴力団との取引禁止・暴排ステッカー普及など、'
     '工藤會への市民側からの圧力枠組みが整備された。'
     '全国の暴排条例整備の先進事例。',
     None, None, None, '平成抗争', '司法側', 3),

    ('fukuoka_pref_assembly', 'nat_bouhai_jorei',
     'designation', '2010-2011',
     '全国 暴排条例 整備完了',
     '2010-2011年にかけて全47都道府県で暴力団排除条例が整備された。'
     '工藤會を含む指定暴力団への市民側圧力の法的枠組みが全国規模で確立。',
     None, None, None, '平成抗争', '司法側', 3),

    # ===== 周辺九州地場組織 =====
    ('kurume_dojinkai_hq', 'nat_taishu_kai_zoku',
     'lore', '2010s',
     '太州会(田川)・福博会(福岡市)の併走',
     '九州地場の指定暴力団には他に田川拠点の太州会、福岡市拠点の福博会、長崎の旭琉会など。'
     '工藤會は九州内で最も「市民を直接標的にする」例外的組織として位置づけられた。',
     None, None, None, '平成抗争', '道仁会系', 2),

    # ===== 警察白書ベース全国推移 =====
    ('kudokai_hq_kandake', 'nat_npa_white_full',
     'lore', '2010-2024',
     '警察白書による全国情勢推移',
     '警察白書では、全国の指定暴力団構成員数が2010年代に大幅減少。'
     '工藤會は減少率の中でも特に大きいグループとして取り上げられる。'
     '頂上作戦・本部解体・特定危険指定の効果として位置づけ。',
     None, None, None, '解体後', '司法側', 3),

    # ===== OFAC 継続レビュー =====
    ('ofac_treasury_designation', 'nat_ofac_2024_review',
     'sanctions', '2014-2024',
     'OFAC TCO 指定 継続レビュー',
     '米財務省 OFAC は指定の継続レビューを定期的に実施。'
     '工藤會の TCO 指定は本部解体・トップ判決後も維持されている。',
     None, None, None, '解体後', '司法側', 2),

    ('ofac_treasury_designation', 'nat_state_dept_reward',
     'sanctions', '2013-',
     '米国務省 Rewards for Justice',
     '米国務省「司法のための報奨」プログラムが Transnational Criminal Organization 関連の '
     '情報提供に懸賞金を設定。工藤會を含む TCO 指定組織が対象。',
     None, None, None, '平成抗争', '司法側', 3),
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

    inserted = 0
    missing = set()
    for (slug, src_key, kind, date, title, summary, victim, weapon, resolution,
         era, faction, severity) in EVENTS:
        site_id = s_ids.get(slug)
        if site_id is None:
            missing.add(slug)
            continue
        src_id = src_ids.get(src_key)
        cur.execute(
            'DELETE FROM event WHERE site_id=? AND COALESCE(happened_on,"")=? AND title=?',
            (site_id, date or '', title),
        )
        cur.execute(
            'INSERT INTO event(kind, happened_on, site_id, title, summary, '
            ' victim_role, weapon, resolution, source_id, era_tag, faction_tag, severity) '
            ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
            (kind, date, site_id, title, summary, victim, weapon, resolution,
             src_id, era, faction, severity),
        )
        inserted += 1

    con.commit()
    n = con.execute('SELECT COUNT(*) FROM event').fetchone()[0]
    print(f'phase14_national: +{inserted} events; total events={n}')
    if missing:
        print(f'  WARN: missing slugs: {sorted(missing)}')
    con.close()


if __name__ == '__main__':
    main()
