# OSINT Starter Template

Kokura Underworld Map で実証した OSINT 可視化のスキーマ・パイプライン・
レンダリングを、**別テーマで一から始めるための雛形** です。

## 使い方

```bash
# 1. このディレクトリをコピーして新規プロジェクト作成
cp -r templates/osint-starter ../my-new-investigation
cd ../my-new-investigation

# 2. SITES を編集して題材のサイトを入れる
$EDITOR init_db.py

# 3. DB を初期化
python init_db.py

# 4. データを段階的に拡充(phase スクリプトを書く)
python phase01_basic.py

# 5. HTML をビルド
python dash.py

# 6. ブラウザで index.html を開く
xdg-open index.html
```

## 含まれるもの

- `init_db.py` — スキーマ定義 + 最小サンプル拠点
- `dash.py` — 単一 HTML レンダラ(地図 + 詳細パネル)
- `phase01_basic.py` — narration / event を追加するサンプル phase
- `vendor/leaflet/` — Leaflet 1.9.4(自己ホスト)
- `.gitignore` — 標準
- `README.md` — このファイル

## 設計方針

- **冪等な phase スクリプト**: re-run しても自分の行だけ入れ替え
- **provenance 必須**: 全コンテンツに `created_by`(human/llm/scraper)を記録
- **単一 HTML 出力**: GitHub Pages にそのまま置ける
- **データ駆動 UI**: JSON ペイロード埋め込み、JavaScript で全体描画

詳しい設計思想は本リポジトリの [METHODOLOGY.md](../../METHODOLOGY.md)、
スキーマは [SCHEMA.md](../../SCHEMA.md) を参照。

## 適用例(想定テーマ)

このスキーマは組織犯罪以外にも以下に転用できます:

- 災害復興史(東日本大震災・能登地震)
- 産業史(工場・鉱山・物流網の盛衰)
- 政治史(政党・選挙区・政治家系譜)
- 文化史(芸術運動・出版社・劇場)
- 公衆衛生史(感染症・薬害)
- 都市史(再開発・廃線・空き家)

`faction_tag` を `political_party_tag` / `industry_tag` 等に読み替えれば、
基本的な多軸可視化はそのまま動きます。
