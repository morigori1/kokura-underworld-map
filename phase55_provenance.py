"""Phase 55: provenance 列を追加して、データの出所をスキーマで追跡可能に。

ユーザー方針:
  「データの provenance(誰がいつ書いた・どの世代の情報か)が記録されてない」
  → schema 設計の事後修正として provenance を全コンテンツ系テーブルに追加。

追加列(全コンテンツ系):
  - created_by  : 'human:<name>' / 'llm:<model>' / 'scraper:<src>'
  - created_at  : YYYY-MM-DD
  - verified_by : 'human:<name>'(検証者・任意)
  - verified_at : YYYY-MM-DD(検証日・任意)

backfill 方針:
  - 既存 narration / life_snippet / lore / event は 'llm:claude-opus-4-7-1m'
    として記録(これらの大半は LLM 生成のため)
  - 公式報道に基づく source_id 付きの event は 'human:morigori' に
    後で手動更新する余地を残す
  - 全エントリの created_at は 2026-05(本日)に統一(細かい日付は不明)

dash5.py 側で created_by='llm:*' を「要検証」フラグとして UI 表示できる。

Idempotent.
"""
from __future__ import annotations
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'kokura.db')


PROVENANCE_DEFAULT_LLM = 'llm:claude-opus-4-7-1m'
TODAY = '2026-05-25'


def column_exists(cur, table, col):
    return any(r[1] == col for r in cur.execute(f'PRAGMA table_info({table})').fetchall())


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    targets = ['narration', 'life_snippet', 'lore', 'event']
    for t in targets:
        for col, typ in [
            ('created_by', 'TEXT'),
            ('created_at', 'TEXT'),
            ('verified_by', 'TEXT'),
            ('verified_at', 'TEXT'),
        ]:
            if not column_exists(cur, t, col):
                cur.execute(f'ALTER TABLE {t} ADD COLUMN {col} {typ}')
                print(f'Added {t}.{col}')

    # Backfill — all existing rows get LLM default
    for t in targets:
        n = cur.execute(
            f'UPDATE {t} SET created_by = ?, created_at = ? '
            f'WHERE created_by IS NULL OR created_by = ""',
            (PROVENANCE_DEFAULT_LLM, TODAY)
        ).rowcount
        print(f'  {t}: {n} rows backfilled as {PROVENANCE_DEFAULT_LLM}')

    # phase29 / phase42 / phase43 / phase52 で WebSearch 経由で明示的に人間が
    # 修正したものは別途上書きすべきだが、今回は一律 LLM とする(後で個別更新可)。

    # 例外: phase50 (dialect cleanup) で削除したもの以外で、現地者
    # フィードバックを反映した修正は 'human:morigori' とマーク
    # → 該当は narration id=525 (堺町お兄さん中立化) と narration id=212 (ホルモン)
    cur.execute(
        "UPDATE narration SET created_by = 'human:morigori', created_at = ? "
        "WHERE id IN (525, 212)",
        (TODAY,))
    print(f'  Marked id=525, 212 as human-verified after local feedback')

    # 結果サマリ
    print('\n=== Provenance summary ===')
    for t in targets:
        rows = cur.execute(
            f'SELECT created_by, COUNT(*) FROM {t} GROUP BY created_by'
        ).fetchall()
        print(f'  {t}:')
        for r in rows:
            print(f'    {r[0]}: {r[1]}')

    con.commit()
    con.close()


if __name__ == '__main__':
    main()
