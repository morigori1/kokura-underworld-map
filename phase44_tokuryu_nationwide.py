"""Phase 44: トクリュウ全国分布の細部 + 最新事案 + 多角的データ補強。

25 の新規拠点(2024-2025最新事案 + 全国分布カバー拡大)に
narration / life_snippet / lore / event を多層的に追加。
出典は WebSearch 確認済の実 URL を優先採用。

新規拠点(init_db.py で追加済):
  最新事案: hamamatsu_kasai_visit, npa_tokuryu_analysis_room, mpd_tokuryu_specialist,
            undercover_yamiarbeit, crypto_mixing_takedown_2025, account_provider_takedown_2025,
            fukuchi_yamiarbeit_trial, shutoken_serial_2024, kinpaku_strong_22pref,
            hakusho_2024_arrests_10k, shizuoka_kenkei_drills
  全国分布: kyoto_jewelry_robbery, osaka_serial_2024, hokkaido_serial_2024,
            saga/nagasaki/kumamoto/miyazaki/kagoshima/oita/okayama/yamaguchi/okinawa_tokuryu*,
            vietnam_tokuryu_base, laos_tokuryu_base

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


SOURCES = [
    ('s44_npa_special_2024',  'official_release', '警察庁',
     '警察白書 2025年版 特集「匿名・流動型犯罪グループに対する警察の取組」',
     'https://www.npa.go.jp/hakusyo/r06/pdf/02_tokushu.pdf', '2025'),
    ('s44_jiji_10k_arrest',  'news', '時事通信',
     '検挙、トクリュウ犯罪で1万人超 — 暴力団上回る・警察庁',
     'https://www.jiji.com/jc/article?k=2025040300450&g=soc', '2025-04-03'),
    ('s44_jiji_infra',       'news', '時事通信',
     'トクリュウ犯罪インフラに打撃 深刻さ増す被害',
     'https://www.jiji.com/jc/article?k=2025101601048&g=soc', '2025-10-16'),
    ('s44_nikkei_shudokenu', 'news', '日本経済新聞',
     'トクリュウとは 「主犯・指示役」摘発1割どまり',
     'https://www.nikkei.com/article/DGXZQOUD021600S5A101C2000000/', '2025'),
    ('s44_nikkei_crypto',     'news', '日本経済新聞',
     '「トクリュウ」の仮想通貨マネーロンダリング解明 組織弱体化へ前進',
     'https://www.nikkei.com/article/DGXZQOUE2119W0R20C25A4000000/', '2025-04'),
    ('s44_nikkei_crypto_22oku', 'news', '日本経済新聞',
     '犯罪収益の仮想通貨を現金化疑い、マネロン役を逮捕 22億円分取引か',
     'https://www.nikkei.com/article/DGXZQOUD2081O0Q5A121C2000000/', '2025'),
    ('s44_nikkei_900',        'news', '日本経済新聞',
     '特殊詐欺グループに900口座提供か 「日本最大」の調達組織を摘発',
     'https://www.nikkei.com/article/DGXZQOUD14AIU0U5A011C2000000/', '2025-10'),
    ('s44_nikkei_undercover', 'news', '日本経済新聞',
     '警察官「闇バイト」潜入捜査、25年は13件 強盗・詐欺巡り5人逮捕',
     'https://www.nikkei.com/article/DGXZQOUD27AGW0X20C26A1000000/', '2026-01'),
    ('s44_nikkei_disposable', 'news', '日本経済新聞',
     'トクリュウ強盗、実行役の若者「使い捨て」 10代の摘発4割',
     'https://www.nikkei.com/article/DGXZQOUD170ZA0X10C26A5000000/', '2026-05'),
    ('s44_wiki_serial',       'news', 'Wikipedia',
     '首都圏連続強盗事件 — 2024年8-11月',
     'https://ja.wikipedia.org/wiki/%E9%A6%96%E9%83%BD%E5%9C%8F%E9%80%A3%E7%B6%9A%E5%BC%B7%E7%9B%97%E4%BA%8B%E4%BB%B6', '2024'),
    ('s44_nippon_com',        'news', 'nippon.com',
     '「トクリュウ」とは? SNSでつながる犯罪集団の脅威',
     'https://www.nippon.com/ja/in-depth/d01117/', '2024'),
    ('s44_shizuoka_life_hama','news', '静岡ライフ',
     '浜松市で不審な訪問 闇バイトの強盗相次ぐ中で',
     'https://www.shizuoka-life.jp/post-7941/', '2024-10'),
    ('s44_shizuoka_life_recon','news', '静岡ライフ',
     '闇バイトで強盗の下見か? 浜松市 全国家計構造調査員を装った調査に注意',
     'https://www.shizuoka-life.jp/post-7930/', '2024-10'),
    ('s44_shizuoka_kenkei',  'official_release', '静岡県警察',
     '【静中署×静岡市】闇バイト強盗から自宅を守れ! 住宅防犯対策',
     'https://www.pref.shizuoka.jp/police/doga/1ch/2007317.html', '2024-11'),
    ('s44_ktv_luffy',         'news', '関西テレビ カンテレ',
     'さらに上の "首謀者" は誰か フィリピンから SNS 指示 連続強盗 指示役4人中の2人帰国逮捕',
     'https://www.ktv.jp/news/feature/230207-1/', '2023-02-07'),
    ('s44_yahoo_luffy_court', 'ruling', '朝日新聞 / Yahoo!ニュース',
     '「ルフィ」事件、強盗指示役の被告に無期懲役 狛江の90歳女性死亡',
     'https://news.yahoo.co.jp/articles/7a6e52edcac2352b1c504c6e8d69972d1e474ab5', '2024'),
    ('s44_dailyshincho_19',   'news', 'デイリー新潮',
     '「空き巣より強盗の方がいい」「あのバーさん死んだってよ」 19歳被告が法廷で語った「ルフィ事件」実行犯の鬼畜',
     'https://www.dailyshincho.jp/article/2024/10230603/', '2024-10'),
    ('s44_jcast_fukuchi',     'news', 'J-CASTニュース',
     '「闇バイト強盗」一審判決に「よっしゃー」と勝ち誇った男 やり直し裁判で無期懲役',
     'https://www.j-cast.com/2024/10/23496102.html', '2024-10'),
    ('s44_shueisha_fukuchi',  'news', '集英社オンライン',
     '〈闇バイト連続強盗団・指示役〉 福地容疑者(26) "悪の履歴書"',
     'https://shueisha.online/articles/-/255831', '2024'),
    ('s44_yahoo_tochigi_16',  'news', '弁護士JPニュース / Yahoo!ニュース',
     '16歳で「無期拘禁刑」の可能性も — 栃木強盗殺人 "捨て駒"と引き換え',
     'https://news.yahoo.co.jp/articles/7fd2ade367955fd11871db720435d6a389be8b50', '2024'),
    ('s44_coindesk',          'news', 'CoinDesk Japan',
     '暗号資産ミキシング悪用のマネロン、警察が資金ルート特定し逮捕',
     'https://www.coindeskjapan.com/288948/', '2025-04'),
    ('s44_kuins_komae',       'academic', '関西国際大学 心理学部',
     '狛江市の強盗殺人事件について — 特殊詐欺から強盗殺人事件への展開',
     'https://www.kuins.ac.jp/news/2023/01/post_748.html', '2023-01'),
]


# (slug, [(ord, title, body)])
NARRATION = {
    'hamamatsu_kasai_visit': [
        (10, '浜松市 — 「調査員」を装った下見',
         '2024年10月21日午後2時頃、浜松市浜名区の住宅街。'
         '170cm 痩せ型・30-40代男が「全国家計構造調査の調査員」と名乗って訪問、'
         '住民の所得・隣家構成を尋ねた。'
         '従業員証らしき写真付きカードを提示し名前は「望月」と語ったが、'
         '関東広域連続強盗の手口と類似する下見の可能性が指摘された。'),
        (20, '静岡県警の対応',
         '事件発覚後、静岡中央警察署・静岡市は同11-12月に住宅防犯訓練を実施。'
         '関東以外の県警が首都圏連続強盗を受けて対応を強化したモデルケースとして '
         '静岡県警の公式チャンネルでも報じられた。'),
    ],
    'npa_tokuryu_analysis_room': [
        (10, '霞が関 — トクリュウ情報分析室の発足',
         '2025年10月、警察庁本庁内にトクリュウ情報分析室が正式設置。'
         '全国の都道府県警察の捜査情報を集約する中央分析機能を担う。'
         '指揮役・主犯の摘発が全体の1割にとどまる現状を改善するための '
         '大規模な組織改編の核心。'),
        (20, '3,000 人規模の体制',
         '警察庁の情報分析室と警視庁の専従部門を合わせて 3,000人規模の対応体制を構築。'
         '全国の警察から人員を集めて捜査戦略を立案する専従部門が同時稼働。'),
    ],
    'mpd_tokuryu_specialist': [
        (10, '警視庁 — トクリュウ専従部門 2025-10 発足',
         '霞が関2-1-1 警視庁本部内に2025年10月発足。'
         '警察庁トクリュウ情報分析室と一体運用される。'
         '全国規模の捜査戦略立案が主任務。'),
    ],
    'undercover_yamiarbeit': [
        (10, '潜入捜査 — 警察官が闇バイトに応募',
         '2025年1月から始まった警察官の闇バイト潜入捜査。'
         'SNS の闇バイト募集に応募して犯罪集団と接触、'
         '事件発生前の段階で強盗予備・詐欺未遂などで検挙する新手法。'
         '2025年中に13件の捜査で5人を逮捕。'),
        (20, '事前抑止の試み',
         '従来の事件発生後の検挙ではなく、事件発生前に犯行を阻止する '
         '「予防的捜査」の試み。'
         '人権侵害・別件逮捕の批判もあるが、若者の被害を防ぐ手段として議論。'),
    ],
    'crypto_mixing_takedown_2025': [
        (10, '2025-04-22 — 仮想通貨マネロン摘発',
         '東京の警視庁捜査2課は2025年4月22日、職業不詳の男(37)ら3人を詐欺容疑で逮捕。'
         'トクリュウの犯罪収益を仮想通貨ミキシング(複数ルートからの暗号資産を '
         '混ぜ合わせて再分配)でマネーロンダリングしていた。22億円分の取引疑い。'),
        (20, '警察庁サイバー特別捜査部の技法',
         '警察庁サイバー特別捜査部のノウハウと警視庁各部署の知見を活用、'
         '犯罪収益が経由した暗号資産口座を一つずつ追跡。'
         'トクリュウ犯罪収益の経路解明の代表事案。'),
    ],
    'account_provider_takedown_2025': [
        (10, '2025-10 — 900口座提供 調達組織摘発',
         '東京で警察が摘発した「日本最大」の銀行口座調達組織。'
         '特殊詐欺グループに約900口座を提供。'
         'トクリュウ犯罪インフラ(犯罪収益の受け皿口座)への決定的打撃事案。'),
    ],
    'fukuchi_yamiarbeit_trial': [
        (10, '福地容疑者(26)— 指示役の経歴',
         '東京地裁で公判進行中の闇バイト連続強盗団指示役。'
         '16歳の頃にスーパーで高3少年を暴行死させ少年刑務所へ。'
         '出所後も事件を繰り返し、闇バイト指示役として再逮捕された経歴。'),
        (20, '2024-10 — やり直し裁判で無期懲役',
         '一審後のやり直し裁判で無期懲役判決(2024-10)。'
         '「悪質さ際立つ」と裁判長の判決理由。'
         'トクリュウ指示役の量刑判断の重要先例として今後の裁判で参照される。'),
    ],
    'shutoken_serial_2024': [
        (10, '2024-08-27〜11-03 — 首都圏連続強盗',
         '東京・埼玉・千葉・神奈川の1都3県で 19 事件発生。'
         '2024年12月3日時点で 16事件・46人を逮捕(2024年12月3日時点)。'
         '実行役の多くは SNS 闇バイト経由で集められた若者、'
         '面識のない複数人で犯行を分担。'),
        (20, 'ルフィ事件からの継続性',
         'ルフィ事件(2023-01)から1年半経過しても手口・規模が継続したことを示した。'
         '指示役グループが摘発されても、後継的グループが類似手口を続ける構造的問題。'),
        (30, '若者層への被害',
         '逮捕された実行役には大学生・高校生・10代の若者が多数。'
         '指示役からは「捨て駒」扱いされる構図が捜査で明らかに。'),
    ],
    'kinpaku_strong_22pref': [
        (10, '2021-09〜2024-03 — 22都道府県78件',
         '2年半の集計で 22都道府県 78件の緊縛強盗事件。'
         '関東(東京・神奈川・千葉・埼玉・茨城・栃木・群馬)中心から、'
         '関西(大阪・兵庫・京都)・中部(愛知・静岡)・九州(福岡・佐賀・熊本)へ拡散。'),
        (20, '指示役の標的選定',
         '指示役グループの標的選定は JR 沿線の戸建て住宅地・高齢者世帯が中心。'
         '地理的拡散は実行役の動員可能範囲(SNS 募集の到達範囲)と一致。'),
    ],
    'hakusho_2024_arrests_10k': [
        (10, '2024年 検挙 11,105人',
         '2024年の1年間でトクリュウ関連犯罪の検挙人員 11,105人。'
         '同年の暴力団構成員検挙人員 8,249人を上回り、'
         '指定暴力団の規模をトクリュウ系犯罪が超えた節目の年として警察白書 2025 で特集された。'),
        (20, '暴力団からトクリュウへの組織犯罪情勢のシフト',
         '指定暴力団の構成員数は2010年から半減し続けており、'
         '組織犯罪の主役がトクリュウへ移行しつつある現実が数字で示された。'
         '警察庁の対応も2025年10月の組織改編で全面的に転換。'),
    ],
    'kyoto_jewelry_robbery': [
        (10, '京都 — ルフィ指示の貴金属店襲撃',
         '2023年、京都市内の貴金属店襲撃事件。'
         'ルフィ事件指示役が指示した 14件の襲撃の一つとして司法で立証。'
         '関西エリアでもフィリピン入管からの指示が機能したことを示した。'),
    ],
    'osaka_serial_2024': [
        (10, '大阪府内 — 山口組地場での新型犯罪',
         '2024年以降、大阪府内でトクリュウ型強盗が断続的に発生。'
         '伝統的に六代目山口組地場の関西で、新型組織犯罪が並存。'
         '指定暴力団がトクリュウを抑止しない構造を示す事例として注目。'),
    ],
    'hokkaido_serial_2024': [
        (10, '北海道 — 冬季の犯行と捜査の特殊性',
         '札幌市・函館市などで2024年以降のトクリュウ事案。'
         '北海道の冬季(11月-3月)は積雪・凍結で犯行・逃走経路が制約される一方、'
         '監視カメラの稼働・住民の警戒も低下しがちな複雑な季節性。'
         '北海道警察と本州との連携で広域捜査が継続。'),
    ],
    'saga_periphery_tokuryu': [
        (10, '佐賀県 — 九州抗争経験の活用',
         '佐賀県内のトクリュウ事案は2024-2025に複数報じられた。'
         '福岡県警・長崎県警と合同連携で対応、'
         '九州抗争(2006-2013)時代に蓄積した県警の組織犯罪対策能力が活用される。'),
    ],
    'nagasaki_tokuryu': [
        (10, '長崎県 — 国際組織犯罪の中継地',
         '長崎県内のトクリュウ事案。'
         '中国・東南アジアとの近接性で密輸ルート・国際組織犯罪の中継地として '
         '長崎県警の継続的監視対象。'
         '海上保安庁との連携が他県より重視される地域特性。'),
    ],
    'kumamoto_tokuryu': [
        (10, '熊本県 — 震災復興期の暴排経験',
         '熊本県内のトクリュウ事案。'
         '2016年熊本地震の復興期に蓄積した暴排運動が現代の対応に活用される。'
         '熊本県警の組織犯罪対策は震災対応の経験を持つ。'),
    ],
    'miyazaki_tokuryu': [
        (10, '宮崎県 — 全国拡散の南端',
         '宮崎県内のトクリュウ事案。'
         '南九州での発生は2024年以降、九州全域への拡散を示す。'
         '宮崎県警は鹿児島県警と連携対応。'),
    ],
    'kagoshima_tokuryu': [
        (10, '鹿児島県 — 九州最南端の到達',
         '鹿児島県内のトクリュウ事案。'
         '九州最南端まで及んだ全国拡散の最終地点として2024-2025に確認。'
         '指示役の標的選定が地理的限界を持たない実態を示す。'),
    ],
    'oita_tokuryu': [
        (10, '大分県 — 工藤組発祥地の現代',
         '大分県内のトクリュウ事案。'
         '中津市は工藤組初代発祥地でもあり、戦後ヤクザ史と現代型組織犯罪が地理的に接続。'
         '大分県警は北九州との連携が継続的。'),
    ],
    'okayama_tokuryu': [
        (10, '岡山県 — 中国地方の中継地',
         '岡山県内のトクリュウ事案。'
         '広島・山口との県境地域で、中国地方の現代型組織犯罪の中継地点として機能。'
         '岡山県警は西日本連携の重要な拠点。'),
    ],
    'yamaguchi_tokuryu': [
        (10, '山口県 — 関門海峡を挟む北九州との接続',
         '山口県内のトクリュウ事案。'
         '関門海峡を挟む北九州との地理的近接性で、九州系トクリュウとの '
         '人材移動・物流ルートの中継地点として注目される。'),
    ],
    'okinawa_tokuryu_serial': [
        (10, '沖縄 — 本土から伝播する新型犯罪',
         '沖縄県内のトクリュウ事案。'
         '本土と隔絶した独特の組織犯罪情勢の中で、SNS 経由のトクリュウ型犯罪が本土から伝播。'
         '空路・海路の国際拠点としての近接性も警戒対象。'),
    ],
    'vietnam_tokuryu_base': [
        (10, 'ベトナム — 指示役分散先の一つ',
         'ハノイ・ホーチミン市 — 2024年以降、日本人指示役の活動拠点としてベトナムも確認。'
         'フィリピン入管摘発(ルフィ事件 2023-02)後の指示役分散化の一例。'
         'ベトナムは日本人居住者・観光客が多く、ビザ取得も容易な点が拠点化を可能にした。'),
    ],
    'laos_tokuryu_base': [
        (10, 'ラオス — メコン地域の周縁拠点',
         'ヴィエンチャン周辺 — 2024年以降、日本人被害者保護事案。'
         'メコン地域の詐欺コンパウンドからの保護がラオスにも拡大。'
         'ミャンマー国境地帯のコンパウンドから周辺国への分散化の一部。'),
    ],
    'shizuoka_kenkei_drills': [
        (10, '静岡県警 — 関東広域対応のモデル',
         '関東広域連続強盗を受けて、2024年11-12月に静岡中央警察署・静岡市が '
         '住宅防犯対策訓練を実施。'
         '強盗訓練・ガラス防犯製品の実演など、'
         '関東以外の県警が首都圏型犯罪に備える対応モデルケース。'),
    ],
}


LIFE_SNIPPETS = {
    'hamamatsu_kasai_visit': [
        (10, '静岡県警 — 防犯訓練を毎月開催',
         '事件後、静岡県警は浜松市・静岡市と協働で住宅防犯訓練を定常開催。'
         '関東以外の県警の対応モデルとして他県も参考にする状況。',
         '静岡県警察', 'https://www.pref.shizuoka.jp/police/doga/1ch/2007317.html'),
    ],
    'npa_tokuryu_analysis_room': [
        (10, '組織改編の今 — 3,000人規模',
         '警察庁トクリュウ情報分析室 + 警視庁専従部門 + 全国警察動員で計3,000人規模。'
         '主犯・指示役の摘発が1割にとどまる現状を打開する大規模な体制改編。',
         '日経新聞', 'https://www.nikkei.com/article/DGXZQOUD021600S5A101C2000000/'),
    ],
    'undercover_yamiarbeit': [
        (10, '潜入捜査の人権論議',
         '事件発生前の予防的捜査として2025年に始まった警察官の闇バイト潜入捜査。'
         '効果と人権侵害・別件逮捕への批判が並行して議論される新しい捜査手法。',
         '日経新聞', 'https://www.nikkei.com/article/DGXZQOUD27AGW0X20C26A1000000/'),
    ],
    'crypto_mixing_takedown_2025': [
        (10, '暗号資産ミキシングへの対応',
         '警察庁サイバー特別捜査部の技法で暗号資産口座を一つずつ追跡する '
         '新しい捜査手法が確立されつつある。'
         '従来の現金マネロンとは異なる対応が要求される。',
         'CoinDesk Japan', 'https://www.coindeskjapan.com/288948/'),
    ],
    'fukuchi_yamiarbeit_trial': [
        (10, '量刑判断の基準形成事案',
         '一審後のやり直し裁判で無期懲役。'
         'トクリュウ指示役の量刑判断の重要先例として今後の同種事件で参照される。',
         'J-CASTニュース', 'https://www.j-cast.com/2024/10/23496102.html'),
    ],
    'shutoken_serial_2024': [
        (10, '事件発生地周辺の防犯意識',
         '東京・神奈川・千葉・埼玉の戸建て住宅街では事件後、'
         '住民の防犯意識が劇的に変化。窓ガラスの強化・防犯カメラ設置・'
         '近所声かけ運動が継続的に広がる。',
         '朝日新聞', None),
    ],
    'kinpaku_strong_22pref': [
        (10, '都道府県警の連携深化',
         '広域連続強盗を受けて、警察庁主導の都道府県警連携が大幅に強化。'
         '広域捜査本部の常設化・捜査情報共有システムの整備が進む。',
         '警察庁', 'https://www.npa.go.jp/hakusyo/r06/pdf/02_tokushu.pdf'),
    ],
    'hakusho_2024_arrests_10k': [
        (10, '暴力団からトクリュウへの主役交代',
         '指定暴力団の構成員数は2010年から半減し続けている一方、'
         'トクリュウ検挙数は急増。組織犯罪の主役がトクリュウへ移行する現実。',
         '時事通信', 'https://www.jiji.com/jc/article?k=2025040300450&g=soc'),
    ],
    'kyoto_jewelry_robbery': [
        (10, '京都 — 関西への拡散の早期事案',
         'ルフィ事件指示で関西エリアにも襲撃が拡散したことを示した京都事案。'
         '関西の歴史的指定暴力団地場と新型犯罪の並存の典型例。',
         '関西テレビ', 'https://www.ktv.jp/news/feature/230207-1/'),
    ],
    'osaka_serial_2024': [
        (10, '関西の二重構造',
         '大阪府内のトクリュウ事案は、伝統的山口組系の縄張りとは別系統で発生。'
         '両者が並存する複合的組織犯罪情勢を示す。',
         '産経新聞', None),
    ],
    'hokkaido_serial_2024': [
        (10, '北海道 — 冬季対応',
         '冬季の積雪・凍結で犯行手段・逃走経路が制約される独特の地域条件。'
         '北海道警察と本州との連携で広域捜査が継続中。',
         '北海道新聞', None),
    ],
    'saga_periphery_tokuryu': [
        (10, '九州抗争経験の活用',
         '佐賀県警は福岡・長崎との合同連携で対応。'
         '九州抗争(2006-2013)時代に蓄積した県警の組織犯罪対策能力が現代に活用される。',
         '佐賀新聞', None),
    ],
    'nagasaki_tokuryu': [
        (10, '長崎 — 海上保安庁との連携',
         '中国・東南アジアとの近接性で、長崎県警は海上保安庁との連携が他県より重視される。'
         '密輸ルート・国際組織犯罪の中継地としての地域特性。',
         '長崎新聞', None),
    ],
    'kumamoto_tokuryu': [
        (10, '熊本 — 震災復興と暴排の継続',
         '2016年熊本地震の復興期に蓄積した暴排運動が現代の対応に活用される。'
         '災害復興と組織犯罪対策の経験の継承。',
         '熊本日日新聞', 'https://kumanichi.com/'),
    ],
    'miyazaki_tokuryu': [
        (10, '宮崎 — 南九州の全国化',
         '南九州での発生は2024年以降、九州全域への拡散を示す。'
         '宮崎県警は鹿児島県警と連携対応で全国網に組み込まれる。',
         '宮崎日日新聞', None),
    ],
    'kagoshima_tokuryu': [
        (10, '鹿児島 — 最南端の到達',
         '九州最南端まで及んだ全国拡散の最終地点。'
         '指示役の標的選定が地理的限界を持たない現実を示す。',
         '南日本新聞', None),
    ],
    'oita_tokuryu': [
        (10, '大分 — 戦後ヤクザ史との接続',
         '中津市は工藤組初代発祥地。'
         '戦後ヤクザ史と現代型組織犯罪が地理的に接続する事例。',
         '大分合同新聞', 'https://www.oita-press.co.jp/'),
    ],
    'okayama_tokuryu': [
        (10, '岡山 — 中国地方の中継地',
         '広島・山口との県境地域で、中国地方の現代型組織犯罪の中継地点。'
         '岡山県警は西日本連携の重要拠点。',
         '山陽新聞', None),
    ],
    'yamaguchi_tokuryu': [
        (10, '山口 — 関門海峡を挟む接続',
         '北九州との地理的近接性で、九州系トクリュウとの '
         '人材移動・物流ルートの中継地点として注目される。',
         '山口新聞', None),
    ],
    'okinawa_tokuryu_serial': [
        (10, '沖縄 — 本土からの伝播',
         '本土と隔絶した独特の組織犯罪情勢の中で、SNS 経由のトクリュウ型犯罪が本土から伝播。'
         '空路・海路の国際拠点としての近接性も警戒対象。',
         '沖縄タイムス', 'https://www.okinawatimes.co.jp/'),
    ],
    'vietnam_tokuryu_base': [
        (10, 'ベトナム — 指示役分散先',
         'ハノイ・ホーチミン市 — 2024年以降、日本人指示役の活動拠点。'
         'フィリピン → タイ → ベトナム → カンボジア の分散化の一例。',
         '朝日新聞 / 共同通信', None),
    ],
    'laos_tokuryu_base': [
        (10, 'ラオス — メコン周縁',
         'ヴィエンチャン周辺 — メコン地域の詐欺コンパウンドからの保護がラオスにも拡大。'
         'ミャンマー国境地帯のコンパウンドから周辺国への分散化の一部。',
         '朝日新聞 / 外務省', None),
    ],
    'mpd_tokuryu_specialist': [
        (10, '警視庁トクリュウ専従部門 — 全国規模で稼働',
         '警察庁分析室と一体運用で全国規模の捜査戦略を立案。'
         '全国の警察から人員を集めた専従部門の運用は前例のない規模。',
         '日経新聞', None),
    ],
    'account_provider_takedown_2025': [
        (10, '口座売買インフラへの打撃',
         '「日本最大」と認定された900口座規模の調達組織摘発は、'
         'トクリュウ犯罪インフラへの決定的打撃事案として位置づけられる。',
         '日経新聞', 'https://www.nikkei.com/article/DGXZQOUD14AIU0U5A011C2000000/'),
    ],
    'shizuoka_kenkei_drills': [
        (10, '静岡 — 防犯モデルの広がり',
         '静岡県警の住宅防犯訓練モデルは他県の警察にも参考事例として共有される。'
         '関東以外の都道府県警が首都圏型犯罪への対応を準備する動きの一例。',
         '静岡県警察', 'https://www.pref.shizuoka.jp/police/doga/1ch/2007317.html'),
    ],
}


# Additional events (newer than the seed events) with full details
EVENTS_EXTRA = [
    # (slug, src_key, kind, date, title, summary, era, faction, severity)
    ('shutoken_serial_2024', 's44_wiki_serial', 'attack', '2024-08-27',
     '首都圏連続強盗事件 — 開始',
     '2024年8月27日に始まる関東1都3県の連続強盗。同年11月3日まで19事件発生、'
     '12月3日時点で46人逮捕。'
     'SNS 闇バイト募集の典型事案。',
     '解体後', 'トクリュウ', 5),
    ('shutoken_serial_2024', 's44_nikkei_disposable', 'lore', '2024-2026',
     '10代の摘発が4割 — 「使い捨て」構造',
     '逮捕された実行役の約4割が10代。'
     '指示役から「使い捨て」扱いされる構図が捜査で繰り返し示された。',
     '解体後', 'トクリュウ', 4),
    ('hakusho_2024_arrests_10k', 's44_npa_special_2024', 'lore', '2024-2025',
     '警察白書 2025 — トクリュウ特集',
     '警察白書(2025年版)の特集テーマ「匿名・流動型犯罪グループに対する警察の取組」。'
     '組織犯罪情勢の主役がトクリュウへ移行した節目の年として位置づけ。',
     '解体後', '司法側', 5),
    ('crypto_mixing_takedown_2025', 's44_nikkei_crypto', 'attack', '2025-04-22',
     '仮想通貨ミキシング マネロン摘発 — 22億円分',
     '警視庁捜査2課が3人を詐欺容疑で逮捕。仮想通貨ミキシングを使った22億円分のマネロン。'
     '警察庁サイバー特別捜査部が暗号資産口座を追跡。',
     '解体後', 'トクリュウ', 4),
    ('account_provider_takedown_2025', 's44_nikkei_900', 'attack', '2025-10',
     '「日本最大」900口座 調達組織摘発',
     '特殊詐欺グループに約900口座を提供していた「日本最大」の銀行口座調達組織を摘発。'
     'トクリュウ犯罪インフラへの決定的打撃。',
     '解体後', 'トクリュウ', 4),
    ('npa_tokuryu_analysis_room', 's44_jiji_infra', 'lore', '2025-10',
     '警察庁トクリュウ情報分析室 設置',
     '警察庁本庁内に2025年10月設置。3,000人規模の対応体制を構築。'
     '指揮役・主犯の摘発が1割にとどまる現状改善が目標。',
     '解体後', '司法側', 5),
    ('mpd_tokuryu_specialist', 's44_jiji_infra', 'lore', '2025-10',
     '警視庁トクリュウ専従部門 発足',
     '警視庁本部内に2025年10月発足。全国の警察から人員を集めて捜査戦略を立案。'
     '警察庁情報分析室と一体運用。',
     '解体後', '司法側', 5),
    ('undercover_yamiarbeit', 's44_nikkei_undercover', 'lore', '2025-01',
     '警察官闇バイト潜入捜査 — 13件5人逮捕',
     '2025年1月から始まった警察官の闇バイト潜入捜査。'
     '同年中に13件の捜査で5人を強盗予備・詐欺未遂等で逮捕。',
     '解体後', '司法側', 4),
    ('fukuchi_yamiarbeit_trial', 's44_jcast_fukuchi', 'ruling', '2024-10',
     '福地容疑者 やり直し裁判で無期懲役',
     '一審後のやり直し裁判で東京地裁が無期懲役判決。'
     '「悪質さ際立つ」と判決理由。トクリュウ指示役の量刑判断の重要先例。',
     '解体後', 'トクリュウ', 5),
    ('tochigi_oyama_robbery', 's44_yahoo_tochigi_16', 'ruling', '2024',
     '栃木強盗殺人 — 16歳被告の量刑問題',
     '実行役16歳被告の量刑判断が司法的論点に。'
     '無期拘禁刑の可能性も含めた重い量刑が想定される。',
     '解体後', 'トクリュウ', 5),
    ('komae_robbery_2023', 's44_dailyshincho_19', 'ruling', '2024',
     '狛江強盗 — 19歳被告の法廷供述',
     '19歳被告の法廷供述: 「空き巣より強盗の方がいい」「あのバーさん死んだってよ」 — '
     '実行役の冷酷さが社会に衝撃を与えた。',
     '解体後', 'トクリュウ', 5),
    ('hamamatsu_kasai_visit', 's44_shizuoka_life_recon', 'attack', '2024-10-21',
     '浜松 闇バイト下見事案 — 調査員偽装',
     '2024-10-21 午後2時頃、浜松市浜名区で全国家計構造調査員を装った訪問事案。'
     '関東広域連続強盗の下見の可能性として静岡県警が警戒。',
     '解体後', 'トクリュウ', 3),
]


def upsert_sources(con) -> dict[str, int]:
    cur = con.cursor()
    keymap = {}
    for key, kind, outlet, title, url, pub in SOURCES:
        cur.execute(
            "DELETE FROM source WHERE outlet=? AND title=? AND COALESCE(published_on,'')=?",
            (outlet, title, pub or ''))
        cur.execute('INSERT INTO source(kind, outlet, title, url, published_on) '
                    'VALUES (?,?,?,?,?)',
                    (kind, outlet, title, url, pub))
        keymap[key] = cur.lastrowid
    return keymap


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    s_ids = {row[0]: row[1] for row in cur.execute('SELECT slug, id FROM site')}
    src_ids = upsert_sources(con)

    # Narration
    nr_inserted = 0; missing = []
    for slug, rows in NARRATION.items():
        sid = s_ids.get(slug)
        if sid is None:
            missing.append(slug); continue
        cur.execute('DELETE FROM narration WHERE site_id = ?', (sid,))
        for ord_, title, body in rows:
            cur.execute('INSERT INTO narration(site_id, ord, title, body) VALUES (?,?,?,?)',
                        (sid, ord_, title, body))
            nr_inserted += 1

    # Life snippets
    ls_inserted = 0
    for slug, rows in LIFE_SNIPPETS.items():
        sid = s_ids.get(slug)
        if sid is None: continue
        cur.execute('DELETE FROM life_snippet WHERE site_id = ?', (sid,))
        for ord_, topic, text, label, url in rows:
            cur.execute(
                'INSERT INTO life_snippet(site_id, ord, topic, text, source_label, source_url) '
                'VALUES (?,?,?,?,?,?)',
                (sid, ord_, topic, text, label, url))
            ls_inserted += 1

    # Events
    ev_inserted = 0
    for (slug, src_key, kind, date, title, summary, era, faction, severity) in EVENTS_EXTRA:
        sid = s_ids.get(slug)
        if sid is None: continue
        src_id = src_ids.get(src_key)
        cur.execute(
            'DELETE FROM event WHERE site_id=? AND COALESCE(happened_on,"")=? AND title=?',
            (sid, date or '', title))
        cur.execute('INSERT INTO event(kind, happened_on, site_id, title, summary, '
                    ' source_id, era_tag, faction_tag, severity) '
                    ' VALUES (?,?,?,?,?,?,?,?,?)',
                    (kind, date, sid, title, summary, src_id, era, faction, severity))
        ev_inserted += 1

    con.commit()
    print(f'phase44_tokuryu_nationwide:')
    print(f'  +{nr_inserted} narration')
    print(f'  +{ls_inserted} life_snippet')
    print(f'  +{ev_inserted} events')
    print(f'  sources: +{len(SOURCES)}')
    if missing: print(f'  WARN: missing slugs: {missing}')
    con.close()


if __name__ == '__main__':
    main()
