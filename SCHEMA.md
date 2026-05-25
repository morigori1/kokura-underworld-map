# SCHEMA — データベース構造リファレンス

`kokura.db`(SQLite)のテーブル構造を、用途・運用ポリシーとあわせて記録します。

このスキーマは、組織犯罪マップ以外の OSINT プロジェクトにも転用可能なように
**ドメイン非依存** に設計されています。

---

## 全体図

```
                    place(地理単位)
                       │ 1 : N
                       ▼
                     site(地図上の点)──┬─→ event(事件)
                       │               ├─→ lore(軼話)
                       │               ├─→ narration(解説段落)
                       │               ├─→ life_snippet(街のいま)
                       │               ├─→ local_media(地元メディア)
                       │               ├─→ testimony(証言)
                       │               ├─→ imagery(衛星フレーム)
                       │               ├─→ image_resource(写真)
                       │               └─→ poi(周辺施設)
                       │
                     person(人物)
                       │
                     org_tree(組織系統樹)

                     chronicle(年表 — 全体)
                     prosecution(訴訟 — 全体)
                     source(出典 — 横断参照)
                     crime_stat(統計時系列)
```

---

## コアテーブル

### `site` — 地図上の点

| 列名 | 型 | 用途 |
|---|---|---|
| `id` | INTEGER PK | 内部 ID |
| `slug` | TEXT NOT NULL | URL-safe な識別子 (`kudokai_hq_kandake` 等) |
| `label` | TEXT NOT NULL | 表示名 (`工藤會本部跡(神岳)`) |
| `place_id` | INTEGER FK | `place` テーブルへの参照 |
| `rep_lat` | REAL | 代表緯度 |
| `rep_lon` | REAL | 代表経度 |
| `uncertainty_m` | INTEGER | 座標の不確かさ(m)|
| `kind` | TEXT | 種別 (`hq_former` / `attack_site` / `district` / `lore_site` / `landmark`) |
| `first_seen` | TEXT | 最初の関連年 |
| `last_seen` | TEXT | 最終の関連年(継続中なら NULL)|
| `status` | TEXT | `active` / `demolished` / `relocated` |
| `notes` | TEXT | 拠点 1 行説明(地理 + 簡単な経緯)|
| `era_tag` | TEXT | 時代タグ(`戦後闇市` / `高度成長` / `平成抗争` / `頂上作戦` / `解体後`)|
| `faction_tag` | TEXT | 派閥タグ(`工藤組系` / `田中組系` / `半グレ` / `トクリュウ` / `司法側` / `市民側` 等)|

**運用ポリシー**:
- `slug` は永久不変(変更すると外部リンクが壊れる)
- 被害者宅は町丁目重心で十分(番地は記載しない)
- 公的建物は正確住所を記載
- `era_tag` と `faction_tag` の組み合わせで色分けモードが切り替わる

---

### `event` — サイトに紐づく事件

| 列名 | 型 | 用途 |
|---|---|---|
| `id` | INTEGER PK | |
| `site_id` | INTEGER FK | `site.id` |
| `kind` | TEXT | `attack` / `arrest` / `ruling` / `lore` |
| `happened_on` | TEXT | YYYY-MM-DD または YYYY-MM |
| `title` | TEXT | 短いタイトル |
| `summary` | TEXT | 1-3 段落の要約 |
| `victim_role` | TEXT | 「元漁協理事」「歯科医師」 等(氏名は載せない)|
| `weapon` | TEXT | 「散弾銃」「金属バット」 等 |
| `resolution` | TEXT | 「未解決」「○○年判決」 等 |
| `source_id` | INTEGER FK | `source.id` |
| `era_tag` | TEXT | |
| `faction_tag` | TEXT | |
| `severity` | INTEGER | 1-5(タイムラインの目立ち具合)|

---

### `narration` — サイトに紐づく解説段落

| 列名 | 型 | 用途 |
|---|---|---|
| `id` | INTEGER PK | |
| `site_id` | INTEGER FK | |
| `ord` | INTEGER | 表示順(10, 20, 30...)|
| `title` | TEXT | 段落のサブタイトル |
| `body` | TEXT | 段落本文(1-3 文)|
| `created_by` | TEXT (新) | `human` / `llm` / `scraper`(provenance)|
| `created_at` | TEXT (新) | YYYY-MM-DD |
| `source_id` | INTEGER FK (任) | 出典 |

**運用ポリシー** (phase 55 で追加):
- 全 narration に `created_by` を必須化
- `llm` の場合、現地者の検証なしで「○○固有」「世代記憶」表現は使わない

---

### `life_snippet` — 街のいまカード

| 列名 | 型 | 用途 |
|---|---|---|
| `id` | INTEGER PK | |
| `site_id` | INTEGER FK | |
| `ord` | INTEGER | 表示順 |
| `topic` | TEXT | カード見出し |
| `text` | TEXT | カード本文 |
| `source_label` | TEXT | 出典名(表示用)|
| `source_url` | TEXT | 出典 URL(クリック可)|

---

### `local_media` — 地元メディア・行政

| 列名 | 型 | 用途 |
|---|---|---|
| `id` | INTEGER PK | |
| `site_id` | INTEGER FK | |
| `kind` | TEXT | `newspaper` / `tv` / `radio` / `magazine` / `pref_gov` / `city_gov` / `pref_police` / `bouhai_center` / `court` / `library` / `museum` / `npo` / `other` |
| `name` | TEXT | 組織名 |
| `url` | TEXT | 公式 URL |
| `note` | TEXT | 補足(管轄区域など)|
| `ord` | INTEGER | 表示順 |
| `tier` | TEXT (新) | `city` / `pref` / `intl`(空間階層)|

**運用ポリシー**:
- `tier='city'` を ord=5 に置いて常に上位表示
- 国際拠点は `tier='intl'` で在外日本大使館・現地警察を割り当て

---

### `source` — 出典横断テーブル

| 列名 | 型 | 用途 |
|---|---|---|
| `id` | INTEGER PK | |
| `kind` | TEXT | `news` / `book` / `foreign_press` / `documentary` / `film_ref` / `academic` / `ruling` / `sanctions` / `police_whitepaper` / `legislative_record` / `ngo` / `memoir` / `official_release` |
| `outlet` | TEXT | 媒体名(「西日本新聞」「朝日新聞」「金融庁」 等)|
| `title` | TEXT | 記事タイトルまたは書籍名 |
| `url` | TEXT | URL(homepage / story-specific のどちらも)|
| `published_on` | TEXT | YYYY-MM-DD または YYYY |

**13 種類の `kind`** が色分けの軸になる(news=灰 / ruling=青 / sanctions=赤 等)。

---

## 全体テーブル

### `chronicle` — プロジェクト全体の年表

`site_id` を持たない全体年表。トップレベルのストーリーラインを記述。

### `prosecution` — 訴訟記録

`site_id` を持たず、被告・裁判所・判決をフラットに保持。

### `crime_stat` — 統計時系列

年単位の数値統計(指定暴力団構成員数、検挙人員数 等)を保持。
inline SVG チャートで描画する。

### `org_tree` — 組織系統樹

`child` / `parent` / `kind`(`merged_into` / `dissolved_into` / `offshoot_from` / `direct_subord` / `umbrella`)で組織の親子関係を表現。

### `person` — 人物

| 列名 | 型 | 用途 |
|---|---|---|
| `slug` | TEXT | `taoka_kazuo` 等 |
| `name` | TEXT | 表示名 |
| `name_kana` | TEXT | 読み |
| `role` | TEXT | `boss` / `founder` / `defendant` / `author` / `film_maker` |
| `faction_tag` | TEXT | |
| `born` / `died` | TEXT | |
| `site_id` | INTEGER FK | 関連サイト |
| `body` | TEXT | プロフィール段落 |
| `spice` | INTEGER | 1-5 |
| `source_id` | INTEGER FK | |

**運用ポリシー**: 故人 / 判決公開済被告 / 自著の著者 / 公的役職者のみ実名。

### `testimony` — 証言

| 列名 | 型 | 用途 |
|---|---|---|
| `site_id` | INTEGER FK | |
| `role` | TEXT | `judge` / `prosecutor` / `journalist` / `family` / `police` / `academic` |
| `speaker_label` | TEXT | 「福岡地裁 一審 主任裁判官」など匿名労役 |
| `year` | TEXT | |
| `quote` | TEXT | 引用本文(「」付き)|
| `source_id` | INTEGER FK | |

---

## 補助テーブル

### `place` — 地理単位

| 列名 | 型 | 用途 |
|---|---|---|
| `id` | INTEGER PK | |
| `name_canonical` | TEXT | 「北九州市小倉北区」 等 |
| `admin_country` | TEXT | `JP` / `PH` 等 |
| `admin_state` | TEXT | 「福岡県」 等 |
| `centroid_lat` / `centroid_lon` | REAL | |

### `imagery` — Wayback 衛星画像

各 site の年代別衛星画像 URL。phase4 が自動生成。

### `image_resource` — Wikimedia Commons 写真

| 列名 | 型 | 用途 |
|---|---|---|
| `site_id` | INTEGER FK | |
| `local_path` | TEXT | `images/` 配下のローカルパス |
| `caption` | TEXT | キャプション |
| `credit` | TEXT | 著作権表示 |
| `license` | TEXT | `CC-BY-SA` 等 |
| `source_url` | TEXT | Commons の URL |

### `poi` — 周辺施設(OSM)

OSM Overpass API で取得した警察署・市役所・学校 等。phase5 が自動生成。

### `era_caption` — 衛星タイムマシンの年代キャプション

| 列名 | 型 |
|---|---|
| `site_id` | INTEGER FK |
| `year` | INTEGER |
| `caption` | TEXT |

---

## カラム命名規則

- ID: `id` (PK) / `site_id` `source_id` (FK)
- 表示順: `ord`(10 きざみ、間に挿入余地を残す)
- 日付: `created_on` `happened_on` `decided_on`(`_on` で統一)
- フリーテキスト: `title` `body` `notes` `summary` `text`
- カテゴリ: `kind` `era_tag` `faction_tag` `tier`
- カウント: 整数のみ、null は許可

---

## 次の調査に向けた拡張提案

### `provenance` 列(phase 55 で追加予定)

全コンテンツ系テーブル(`narration` `life_snippet` `lore` `event`)に:

| 列 | 用途 |
|---|---|
| `created_by` | `human:morigori` / `llm:claude-opus-4-7` / `scraper:nhk_archive` |
| `created_at` | YYYY-MM-DD |
| `verified_by` | 検証者(任意) |
| `verified_at` | 検証日時 |

これにより:
- LLM 生成と人間検証済を schema レベルで分離
- 「未検証コンテンツ」を UI でフラグ表示可能
- データの provenance を信頼できる形で記録

### `confidence` 列

事実の確かさを 0-5 で記録:
- 0: 推測 / 不確実
- 1: LLM 生成・未検証
- 3: 報道書籍ベース
- 5: 判決文 / 公的記録

UI で confidence < 3 を点線囲み等で示せば、読者の信頼判断を支援できる。

### `language` 列

`narration.language='ja'` / `'en'` を別レコードで持てば、
バイリンガル化はデータ層から自然に実装可能。
