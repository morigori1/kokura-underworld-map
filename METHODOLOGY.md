# METHODOLOGY — 公開情報統合 OSINT のテストベッド

このプロジェクト(Kokura Underworld Map)は、特定の事件・組織を題材にした
**OSINT 可視化マップ** であると同時に、より広い目的の **テストベッド** です。

> **本当の問い**:
> 公開情報(報道書籍・判決文・警察白書・OFAC SDN・国会議事録・地元紙・
> 自治体公表・OpenStreetMap)を **複数軸で統合** し、
> **時間 × 場所 × 系統 × 出典種別** の多次元で可視化する手法は、
> 別テーマの将来調査にも転用できるか?

このドキュメントは、Kokura ケースで実証した手法と、明らかになった制約を、
**次の調査に再利用するための整理** です。

---

## 1. 検証した手法(うまくいったこと)

### 1.1 段階的レイヤー積み上げ(phase 1-54)

「拠点座標 → POI → 写真 → 解説 → 街のいま → 出典」と層を分けて、
**各層を独立した phase スクリプトで段階的に追加**。

各 phase は **冪等**(re-run で自分の行だけ入れ替え)で書く。

| 利点 |
|---|
| 1 layer 追加 = 1 commit。差分が読める |
| 他の層を壊さずに改善できる |
| 「ここまで自動・ここからは手作業」の境界を可視化 |
| 失敗したフェーズだけ rollback / rewrite できる |

具体的には:

```
init_db.py       → 拠点座標と基本属性(手書き)
phase4_wayback   → Esri Wayback の衛星画像時系列
phase5_poi       → OSM Overpass で周辺施設取得
phase6_events    → 公的事件タイムライン(手書き)
phase7_images    → Wikimedia Commons 写真
phase8_event_imgs → og:image 自動取得
phase9_testimony → 判決抜粋・証言
phase10-29       → 事件・人物・系譜・組織系統樹を地道に追加
phase30-37       → 全国規模に拡張 / 比較対象を追加
phase38-45       → narration と life_snippet を 100% カバー
phase46-48       → 地元メディア・行政の関連付け(都市・県・国際)
phase49-51       → 情感と方言の検証(現地者フィードバック反映)
phase52-54       → URL 補完 + 雑多な街色情報追加
```

### 1.2 単一 HTML + 埋め込み JSON ペイロード

`dash5.py` は SQLite を読んで **全データを JSON 文字列として 1 つの HTML に埋め込む**。

| 利点 |
|---|
| GitHub Pages にそのまま置ける(API・サーバー不要) |
| ブラウザに渡してしまえば即座にインタラクティブ |
| 検索・フィルタ・ツアーが全部クライアントサイドで完結 |
| オフラインでも完全動作(タイルは別だが UI は動く) |

| 制約 |
|---|
| 全データを 1 ファイルに同梱するので肥大化(現在 1.2 MB)|
| 1,000 件以上の拠点になると初期ロードが重い |

### 1.3 多軸タグで「同じデータを異なる視点で」

`era_tag`(時代)・`faction_tag`(派閥)・`source_kind`(出典種別)・
`kind`(拠点種別)を全部のエンティティに持たせ、UI でカラーモードを切り替え。

→ 同じ地図が「時代地図」「派閥地図」「出典マップ」に変身する。

### 1.4 tier 階層(city > pref > intl)による空間グルーピング

`local_media.tier` を使って同じテーブルから「市町村レベル」「都道府県レベル」
「国際レベル」を順次表示。深掘りしたい人は city まで、概観したい人は pref まで。

### 1.5 バイリンガル(data-lang + CSS スイッチ)

`<html lang="ja|en">` を切り替えるだけで、`html[lang="ja"] .i18n-en { display:none }`
の CSS により表示言語が変わる。**JavaScript 一切不要**。

データ層を翻訳しなくても、UI と Splash / Help / About だけ翻訳すれば
海外読者にも届く骨格になる。

### 1.6 ガイドツアー(時系列ナラティブ)

地図上の点群を「いきなり全部見せる」のではなく、**ストーリー順に再生**する
ツアー機能。前/次/一時停止のコントロール付き。

→ 200+ 拠点を初見ユーザーに見せる導入として圧倒的に効く。

---

## 2. 破綻したこと(同じ手は次回避ける)

### 2.1 LLM 生成 narration の検証コスト

「200 拠点の街並み描写を全部 LLM に書かせる」のは効率的に見えるが、
**現地者の目には 1 秒で AI 生成と見抜かれる**。

- 北九州弁(博多弁・筑後弁の混入が即発覚)
- 「観察は正しいが地域固有性を過剰主張」型の文
- 「世代記憶」「うちの○○」など検証不能な代弁

→ **教訓**: LLM 生成と人間検証済を schema レベルで分離する必要がある。
これが今回 `provenance` 列の追加に至る経緯。

### 2.2 出典 URL 補完の規模化

WebSearch で 1 件ずつ実 URL を探す方式は、200+ source には適用しきれない。
現状 54 / 510 source(11%) が story-specific URL を持つだけ。

→ **教訓**: 自動 URL 探索パイプラインが必要(WebFetch + パターンマッチ)。
あるいは、最初から出典 URL を必須にしてデータ投入する制約。

### 2.3 provenance の事後追加

「誰がいつ書いた・どの情報源由来か」を schema に最初から入れておかなかった結果、
500+ narration の真偽を事後判別できない。

→ **教訓**: `created_by`(human/llm/scraper)、`created_at`、
`source_id` を **最初の schema 設計** で必須カラムにすべき。

### 2.4 cleanup の難しさ

54 phase / 350 拠点まで膨らんだ後で全体の品質を見直すと、
**どこを直せばいいか分からなくなる**。

→ **教訓**: 規模が小さいうちにメトリクスを設定する。例えば
「narration 全体の何% が human-verified か」を build 時に表示するなど。

### 2.5 地域固有性の過剰主張

私(LLM)は反射的に「○○ならではの」「○○特有の」「世代記憶の構図」と書きがち。
ほとんどが他の地域でも見られる現象を地域に固有化する誤り。

→ **教訓**: 文章生成時に **「○○固有」を禁止する system prompt** が必要。
あるいは固有性主張のための明示的な「他に類例なし」フラグを source に要求する。

---

## 3. 再利用可能コンポーネント / 次の調査への移植

### 3.1 schema(再利用可)

```
place         地理単位(市町村)
site          地図上の点(label + 座標 + kind + tags)
event         サイトに紐づく事件(日付・summary・出典)
lore          サイトに紐づく軼話(spice 等級)
narration     サイトに紐づく解説段落(複数)
life_snippet  サイトに紐づく「今の街」カード(出典付き)
local_media   サイトに紐づく地元メディア(tier 階層)
person        人物(faction・役割・実名公開ポリシー付き)
testimony     証言(裁判官・検察・記者・被害者支援員 等)
prosecution   訴訟(被告・裁判所・判決)
chronicle     プロジェクト全体の年表
org_tree      組織系統樹(親子・分派・統合・解散)
source        出典(kind・outlet・title・URL・published_on)
narration     解説(各サイト 0-N 段落)
imagery       Wayback 衛星画像フレーム(年月日付き)
image_resource Wikimedia Commons 等の写真
poi           周辺 POI(OSM 由来)
```

このスキーマは、組織犯罪以外でも以下に転用可能:
- 災害史(東日本大震災・能登地震)
- 産業史(工場・鉱山・物流網)
- 政治史(政党・選挙区・政治家系譜)
- 文化史(芸術運動・出版社・劇場)
- 公衆衛生史(感染症・薬害)

`faction_tag` の代わりに `political_party_tag` / `industry_tag` を入れれば、
基本的な多軸可視化はそのまま動く。

### 3.2 phase 設計パターン(再利用可)

```python
"""Phase N: <目的>。

(冪等性: 自分の行だけ DELETE + INSERT、他層は触らない)
"""
def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    s_ids = {row[0]: row[1] for row in cur.execute('SELECT slug, id FROM site')}
    n = 0
    for slug, payload in DATA.items():
        sid = s_ids.get(slug)
        if sid is None: continue
        # 1) 自分の行を消す
        cur.execute('DELETE FROM <table> WHERE site_id=? AND <my_marker>', (sid, ...))
        # 2) 入れ直す
        cur.execute('INSERT INTO <table>(...) VALUES (?,?,?)', (sid, ...))
        n += 1
    con.commit()
    print(f'phase{N}: +{n} rows')
```

このパターンを守る限り、phase はどの順序でも・何度でも実行できる。

### 3.3 dash5.py の構造(再利用可)

```
1. fetch_dicts() で全テーブルを Python dict に読み出す
2. JSON.dumps で JSON 文字列化
3. HTML テンプレートに __PAYLOAD__ 埋め込み
4. JavaScript 側:
   - Leaflet で地図描画
   - 拠点クリック → 詳細パネル(narration / events / lore / life_snippet / local_media)
   - 検索バー(全層横断)
   - フィルタ(faction / era / source_kind)
   - ツアー(時系列ナラティブ再生)
   - 言語切替(html[lang])
```

---

## 4. 次の調査に移植する場合の手順

1. **テーマ選定** — 1 つの地域 / 1 つの組織 / 1 つの時代 など、絞った題材
2. **schema 初期化** — `init_db.py` をコピー、`SITES` を空に
3. **拠点座標を 30-50 件手入力** — Google Maps から手で拾う
4. **phase4(衛星)+ phase5(POI)+ phase7(写真)を流す** — 自動で見栄え
5. **phase6(イベント)を手書きで 100 件** — ここが調査の本体
6. **phase8(og:image)を流す** — イベントカードに視覚厚み
7. **公開可能であれば GitHub Pages に push** — 早い段階で他人に見せる
8. **指摘を受けて修正** — ここで provenance 列の活用が効く

---

## 5. 既知の課題 / 未解決

### 5.1 SNS 共有時のプレビュー

og:image は 1 枚しか指定できないので、拠点ごとの動的 OGP が出せない。
個別拠点を SNS で紹介したい場合、サーバーサイド生成が必要。

### 5.2 検索のスケール

現在 350 拠点で全文検索を毎キーストロークで再計算しているが、
1,000 件超えると重くなる可能性。インデックス(Lunr.js 等)導入を検討。

### 5.3 多言語データ

UI は bilingual だがデータ層(narration / event title)は日本語のみ。
全データ翻訳はコストが大きいので、機械翻訳パイプラインを検討中。

### 5.4 衛星画像のアーカイブ

Esri Wayback は将来サービス停止のリスクがある。
ローカルキャッシュまたは別サービス(Google Earth Engine / Planet)併用が必要。

---

## 6. このプロジェクトを引用する場合

- リポジトリ: <https://github.com/morigori1/kokura-underworld-map>
- 公開 URL: <https://morigori1.github.io/kokura-underworld-map/>
- 姉妹プロジェクト: [Compound Time Machine](https://compoundtimemachine.com)
- 著者: Morigori
- ライセンス: コードは MIT、データは取材源それぞれの権利を尊重

このメソドロジーが、別テーマの調査で再利用された場合、ご一報いただけると
うれしいです。
