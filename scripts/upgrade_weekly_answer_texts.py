#!/usr/bin/env python3
"""Apply the approved compact-learning reply copy to the 2026-08-20 production week."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from threads_automation.content import build_answer_text  # noqa: E402


ANSWERS = {
    "ENG-000006": """💡 正解は B. seeing

look forward to の後ろでは、動作を -ing 形にします。

📝 I'm looking forward to seeing you again.
「またお会いできるのを楽しみにしています。」

🔑 look forward to の後ろは -ing""",
    "ENG-000007": """💡 正解は A. at

officeは到着する「地点」として考えるので、atを使います。

📝 I arrived at the office at 8:30.
「私は8時30分に会社に着きました。」

🔑 at＝地点 / in＝広い場所""",
    "ENG-000008": """💡 正解は A. rolling up

画像では、袖を上へまくる動作をしています。

📝 He is rolling up his sleeves.
「彼は袖をまくっています。」

🔑 roll up one's sleeves＝袖をまくる""",
    "ENG-000009": """💡 正解は A. by Friday

byは、その時点までに終える期限を表します。

📝 I'll send you the file by Friday.
「金曜日までにファイルを送ります。」

🔑 by＝期限 / until＝継続""",
    "ENG-000010": """💡 正解は A. Sure.

Could you ...? という依頼を引き受ける、自然で短い返答です。

🗣️ Sure. I'll turn it on.
「もちろん。つけますね。」""",
    "ENG-000011": """💡 正解は A. That's all, thank you.

追加はないと丁寧に伝えるときの定番表現です。

🗣️ That's all, thank you.
「以上です。ありがとうございます。」""",
    "ENG-000012": """💡 正解は B. goes

Tomは1人で、毎日の習慣を表すのでgoにsを付けます。

📝 Tom goes to work at eight.
「トムは8時に仕事へ行きます。」

🔑 he / she / Tom → 動詞にs""",
    "ENG-000013": """💡 正解は B. was

yesterdayがあるので、過去の状態を表すwasを使います。

📝 I was busy yesterday.
「私は昨日忙しかったです。」

🔑 am＝現在 / was＝過去""",
    "ENG-000014": """💡 正解は A. open

画像ではドアが閉まっておらず、開いた状態です。

📝 The door is open.
「ドアは開いています。」

🔑 open＝開いている""",
    "ENG-000015": """💡 正解は A. by

交通手段を表すときは、乗り物の前にbyを使います。

📝 I go to work by train.
「私は電車で仕事へ行きます。」

🔑 by＋乗り物＝その交通手段で""",
    "ENG-000016": """💡 正解は A. Yes, please.

飲み物の申し出を受ける、丁寧で自然な返答です。

🗣️ Yes, please.
「はい、お願いします。」

🔑 Would you like ...?＝申し出""",
    "ENG-000017": """💡 正解は A. It's near the bank.

場所を聞かれているので、位置を伝える返答が自然です。

🗣️ It's near the bank.
「銀行の近くです。」""",
    "ENG-000018": """💡 正解は A. live

主語がTheyなので、動詞はそのままliveを使います。

📝 They live in Tokyo.
「彼らは東京に住んでいます。」

🔑 I / you / we / they → 動詞はそのまま""",
    "ENG-000019": """💡 正解は A. just

have just finishedで「ちょうど終えたところ」を表します。

📝 I have just finished lunch.
「私はちょうど昼食を終えたところです。」

🔑 have just finished＝ちょうど終えた""",
    "ENG-000020": """💡 正解は A. carrying

画像では、箱を持って運んでいるところです。

📝 She is carrying the box.
「彼女は箱を運んでいます。」

🔑 carry＝持って運ぶ""",
    "ENG-000021": """💡 正解は A. after

昼食が終わった後を表すので、afterを使います。

📝 Please call me after lunch.
「昼食後に電話してください。」

🔑 after lunch＝昼食後""",
    "ENG-000022": """💡 正解は A. You're welcome.

お礼を言われたときに使う定番の返答です。

🗣️ You're welcome.
「どういたしまして。」""",
    "ENG-000023": """💡 正解は A. Sure.

窓を閉めてほしいという依頼を、快く引き受ける返答です。

🗣️ Sure.
「もちろんです。」""",
    "ENG-000024": """💡 正解は B. heavier

thanがあるので、2つを比べるheavierを使います。

📝 This bag is heavier than mine.
「このバッグは私のものより重いです。」

🔑 heavy → heavier""",
    "ENG-000025": """💡 正解は B. are eating

nowがあるので、今している動作を表すare eatingを使います。

📝 We are eating dinner now.
「私たちは今、夕食を食べています。」

🔑 now → be動詞＋-ing""",
    "ENG-000026": """💡 正解は A. empty

画像では、カップの中に何も入っていません。

📝 The cup is empty.
「カップは空です。」

🔑 empty＝空の""",
    "ENG-000027": """💡 正解は A. crowded

画像では、道路に車が多く混み合っています。

📝 The road is crowded.
「道路は混んでいます。」

🔑 crowded＝混雑した""",
    "ENG-000028": """💡 正解は A. at

3 p.m.のような具体的な時刻にはatを使います。

📝 I have a meeting at 3 p.m.
「午後3時に会議があります。」

🔑 at＝時刻 / on＝曜日・日付""",
    "ENG-000029": """💡 正解は A. That's okay.

謝られたときに「大丈夫」と伝える自然な返答です。

🗣️ That's okay.
「大丈夫ですよ。」""",
    "ENG-000030": """💡 正解は A. is

a bankは1つなので、There isを使います。

📝 There is a bank near here.
「この近くに銀行があります。」

🔑 1つならThere is / 複数ならThere are""",
    "ENG-000031": """💡 正解は A. have to

明日早起きする必要があることをhave toで表します。

📝 I have to get up early tomorrow.
「私は明日早起きしなければなりません。」

🔑 have to＝〜する必要がある""",
    "ENG-000032": """💡 正解は A. climbing

画像では、階段を上へ進んでいます。

📝 He is climbing the stairs.
「彼は階段を上っています。」

🔑 climb＝上る""",
    "ENG-000033": """💡 正解は A. because

家にいた理由を続けているので、becauseが自然です。

📝 I stayed home because it was raining.
「雨が降っていたので、家にいました。」

🔑 because＝理由 / so＝結果""",
    "ENG-000034": """💡 正解は A. Of course.

座ってよいか許可を求められたときの自然な返答です。

🗣️ Of course.
「もちろんです。」""",
    "ENG-000035": """💡 正解は A. He plays tennis.

主語がHeなので、playにsを付けた文が正しい形です。

📝 He plays tennis.
「彼はテニスをします。」

🔑 he / she → 動詞にs""",
    "ENG-000036": """💡 正解は A. speak

canの後ろでは、動詞をそのままの形で使います。

📝 Can you speak English?
「英語を話せますか？」

🔑 can＋動詞のそのままの形""",
    "ENG-000037": """💡 正解は A. yet

否定文のyetは「まだ」という意味で、文末に置きます。

📝 I haven't eaten lunch yet.
「私はまだ昼食を食べていません。」

🔑 否定文のyet＝まだ""",
    "ENG-000038": """💡 正解は A. that

thatがbookとI boughtをつなぎ、「私が買った本」を表します。

📝 This is the book that I bought.
「これは私が買った本です。」

🔑 the book that I bought＝私が買った本""",
    "ENG-000039": """💡 正解は A. leaking

画像では、ボトルから液体が漏れています。

📝 The bottle is leaking.
「ボトルから液体が漏れています。」

🔑 leak＝漏れる""",
    "ENG-000040": """💡 正解は A. Could you repeat that?

聞き取れなかったときに、もう一度言ってもらう丁寧な表現です。

🗣️ Could you repeat that?
「もう一度言っていただけますか？」""",
    "ENG-000041": """💡 正解は A. Yes, please.

手伝いの申し出を受ける、丁寧で自然な返答です。

🗣️ Yes, please.
「はい、お願いします。」""",
    "ENG-000042": """💡 正解は B. opens

My officeは1つで、普段の開始時刻なのでopenにsを付けます。

📝 My office opens at nine.
「私の会社は9時に始まります。」

🔑 he / she / 1つのもの → 動詞にs""",
    "ENG-000043": """💡 正解は A. since

2020は始まった時点なので、sinceを使います。

📝 I've known her since 2020.
「私は2020年から彼女を知っています。」

🔑 since＝開始時点 / for＝期間""",
    "ENG-000044": """💡 正解は A. folding

画像では、紙を折っているところです。

📝 She is folding the paper.
「彼女は紙を折っています。」

🔑 fold＝折る""",
    "ENG-000045": """💡 正解は A. on

Monday morningのような曜日を含む表現にはonを使います。

📝 Let's meet on Monday morning.
「月曜日の朝に会いましょう。」

🔑 on＝曜日・日付 / at＝時刻""",
    "ENG-000046": """💡 正解は A. No, it's free.

席が使用中か聞かれたとき、空いていることを伝える返答です。

🗣️ No, it's free.
「いいえ、空いています。」""",
    "ENG-000047": """💡 正解は A. take a break

take a breakで「休憩する」という意味になります。

🗣️ Let's take a break.
「休憩しましょう。」

🔑 take a break＝休憩する""",
}


def main() -> int:
    queue_dir = REPO_ROOT / "data" / "queue"
    master_dir = REPO_ROOT / "data" / "master" / "quiz"
    changed_queues = 0
    for content_id, answer_text in ANSWERS.items():
        master_path = master_dir / f"{content_id}.json"
        master = json.loads(master_path.read_text(encoding="utf-8"))
        master["threads_answer_text"] = answer_text
        build_answer_text(master)
        master_path.write_text(json.dumps(master, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        queue_path = queue_dir / f"{content_id}.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        if queue["status"] == "posted":
            continue
        queue["answer_text"] = answer_text
        queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        changed_queues += 1
    print(f"masters={len(ANSWERS)} queues={changed_queues}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
