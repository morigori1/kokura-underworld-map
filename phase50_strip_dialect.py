"""Phase 50: 北九州弁の誤った例示を削除。

ユーザー(現地者)指摘:
  「ばい」「よかね」「くさ」「たい」は博多弁・筑後弁であり、
  北九州弁ではない。引用部分が間違っているので取り除く。

正しい北九州弁: 「～ちゃ」「～っちゃ」「～っち」「～っちよ」、
「きさん」「なおす(片付ける)」「青じみ(青あざ)」「かしわ(鶏肉)」
「はわく(掃く)」「はらかく(怒る)」「しゃっちが(いつも)」など。

現在のデータでは正しい方言を生成・検証する仕組みがないため、
ユーザーの判断で「方言を引用する箇所は全て削除」する方針。

主な対象:
  narration id=523 (site_id=26 旦過市場 ord=70 「北九州弁の柔らかさ」)
    → 削除(誤った方言例示)
  narration id=525 (site_id=28 堺町 ord=50 「お兄さん」)
    → 「独特の言い回し」表現を一般化(残す)

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

    # 1) site_id=26 (旦過市場) ord=70 の「北九州弁の柔らかさ」narration を削除
    # ユーザーから誤りの指摘: 「よかね」「くさ」「ばい」は北九州弁ではない
    rows = cur.execute(
        "SELECT id FROM narration WHERE site_id = ? AND ord = ? AND title LIKE '%北九州弁%'",
        (26, 70)
    ).fetchall()
    for (rid,) in rows:
        cur.execute('DELETE FROM narration WHERE id = ?', (rid,))
        fixes += 1
        print(f'削除: narration id={rid} (北九州弁の柔らかさ)')

    # phase49_kokura_emotion.py の NARRATION_ADD から該当エントリも
    # コメントアウト相当の DELETE で確実に消す(再 build 時の復活を防ぐ)
    cur.execute("""
        DELETE FROM narration
        WHERE body LIKE '%よかね%'
           OR body LIKE '%これくさ%'
           OR (body LIKE '%ばい%' AND body LIKE '%北九州弁%')
    """)
    extra = cur.execute('SELECT changes()').fetchone()[0]
    if extra > 0:
        print(f'追加削除: {extra} rows with wrong dialect')
        fixes += extra

    # 2) 堺町「お兄さん」narration は方言例ではなく実観察なので残す。
    #    ただし「言い回し」を「呼びかけ」に置き換えて、方言断定を弱める。
    cur.execute(
        "UPDATE narration "
        "SET body = REPLACE(body, '昭和から続く堺町の独特の言い回し。', "
        "  '昭和から続く堺町の独特の呼びかけ。') "
        "WHERE id = ? AND body LIKE '%昭和から続く堺町の独特の言い回し%'",
        (525,)
    )
    if cur.execute('SELECT changes()').fetchone()[0]:
        print('修正: 堺町 narration の「言い回し」→「呼びかけ」')
        fixes += 1

    # 3) 中津市の「工藤の親父」も方言・口語の確認できない引用なので削除する
    cur.execute(
        "UPDATE narration "
        "SET body = REPLACE(body, '関連書籍には「工藤の親父」と呼ぶ地元の言い回しが記録されている。', "
        "  '関連書籍には工藤組の戦後活動史が断片的に記録されている。') "
        "WHERE id = ? AND body LIKE '%工藤の親父%'",
        (371,)
    )
    if cur.execute('SELECT changes()').fetchone()[0]:
        print('修正: 中津 narration の「工藤の親父」を一般表現に')
        fixes += 1

    con.commit()
    print(f'\nTotal fixes: {fixes}')
    con.close()


if __name__ == '__main__':
    main()
