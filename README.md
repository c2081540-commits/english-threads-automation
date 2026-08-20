# English Threads Automation

Instagramと共通の英語学習コンテンツを、Threads向けのクイズスレッドまたは通常投稿queueへ変換します。外部API、AI生成、AIレビュー、投稿処理は含みません。

## 役割と構造

- `data/master/quiz/`: Instagram共通クイズマスターの明示的な投入先
- `data/master/normal/`: Threads本文と将来のStories文面を持つ通常投稿マスター
- `assets/question_images/`: Instagram制作工程から明示投入する共通問題画像fixture
- `config/quiz_hooks.json`: カテゴリ別の短い親フック候補
- `data/queue/`: quiz/normalの生成済みqueue
- `src/threads_automation/`: 検証、共通マスター照合、Threads変換
- `scripts/`: queue生成とdry-run
- `tests/`: 標準ライブラリの単体・統合テスト

## パス規約

全パスは解決済み`__file__`からrepo rootを特定します。クイズマスター、通常投稿マスター、問題画像、設定は固定ディレクトリ直下だけを許可し、探索やfallbackを行いません。コードにユーザー固有の絶対パスはありません。

クイズ生成時は、固定された兄弟repo `english-instagram-automation/data/master/` の正本と `content_id`、`question`、`choices`、`best_answer`、`answer_type`を照合します。Threads側で正解・ヒント・解説を新規生成しません。問題画像は実行時にrepo間参照せず、制作工程が同一画像を`assets/question_images/`へ明示投入します。

## 実行

Python 3.9以降。任意のカレントディレクトリから実行できます。

```bash
python3 /absolute/path/to/english-threads-automation/scripts/build_queue.py quiz ENG-000003
python3 /absolute/path/to/english-threads-automation/scripts/build_queue.py normal ENG-100001
python3 /absolute/path/to/english-threads-automation/scripts/dry_run.py ENG-000003
python3 /absolute/path/to/english-threads-automation/scripts/dry_run.py ENG-100001
python3 -m unittest discover -s /absolute/path/to/english-threads-automation/tests -v
```

## Quiz queue

親本文は問題を繰り返さず、`config/quiz_hooks.json`のカテゴリ候補から`content_id`により決定的に選択します。架空の正答率・多数派・ネイティブ限定などの社会的証明はPythonで拒否します。

子投稿は共通マスターだけから、`考えるポイント → 選択肢記号付き正解 → 短い解説 → 必要な補足`へ整形します。親と回答は同じ`content_id`を持つ1つの完成スレッドとしてqueueに保存します。回答遅延は未実装です。

## Normal queueとStories共通化

通常投稿マスターは以下を保持します。

- `content_id`
- `content_type: normal`
- `theme`
- `threads_text`
- `story_headline`
- `story_body`
- `publish_at`

Threads本文とStories文面を別々に生成せず、同じマスターから各出力へ変換します。

## 無料品質チェック

Pythonで必須項目、文字数、content ID、正答一致、問題画像存在、禁止フック、Instagram正本との共通項目一致を検査します。英語・日本語・素材画像のAIレビューはInstagram側で準備した将来の共通1回レビュー結果を利用し、Threads専用AIレビューは追加しません。

## 将来実装

Meta / Threads API投稿、GitHub Actions、Codex Automation、AI生成、分析、自動最適化、Instagram Storiesテンプレートは今回の対象外です。

## Phase 3 日次試作

`ENG-000006`〜`ENG-000011` はInstagramと同一のquizマスターからThreads表示へ変換し、`ENG-100002` は同一normalマスターから通常投稿へ変換します。既存の `scripts/build_queue.py` と `scripts/dry_run.py` で確認できます。

画像素材がまだないquizはダミー画像や別パスを探索せず、`question_image: null`、`parent_status: WAITING_FOR_VISUAL` で停止します。Threads専用AIレビューは追加せず、共通の7件一括レビュー結果を利用します。

完成済みのvisual問題はInstagramのPillowレンダラーが生成した同一問題画像を `assets/question_images/` へ明示投入します。Phase 3試作では `ENG-000008` と `ENG-000010` がこの状態で、Threads用の別画像は生成しません。

コンテンツの最上位ペルソナは「英語学習に一度挫折し、基礎からやり直したい日本人社会人」です。難化、資格試験的なひっかけ、長い質問と長い回答の比較を品質とは扱いません。Instagram側の `config/content_quality.json` と共通一括レビュー結果を正とし、Threads側で難しい説明や別問題を追加しません。

7日量産テストではInstagram側の共通マスター42件とnormal 7件をそのままqueueへ変換します。完成問題画像があるquizは通常の親＋回答queue、素材待ちのquizは `WAITING_FOR_VISUAL` となります。Threads独自の原稿・画像・AIレビューは生成しません。

シチュエーション問題の `situation_purpose` と `response_family`、Normal投稿の `normal_category` はInstagram側の週次品質検査結果をそのまま共有します。Threads側では別の教材内容や判定基準を生成しません。

## 正式投稿スケジュール

Instagramと同一の `config/schedule.json` を使用し、`python3 scripts/finalize_week_schedule.py YYYY-MM-DD` で確認済み49件をqueueへ確定します。Quizは親投稿と回答返信を同じ `content_id` で保持し、両方の初期状態を `pending` にします。queueは `content_id / platform / publish_at / status` を持ち、`posted` は再投稿対象になりません。

実行時点で過去の枠は日時を変更せず `execution_eligibility: past_due_hold` として保持します。翌日への詰め込みや時刻変更は行いません。自動実行・定期実行は未接続です。

## Phase 6 Meta投稿クライアント

`scripts/run_due_post.py` はqueueから `pending + scheduled + publish_at <= now` の先頭1件だけを選びます。引数なしはAPIを呼ばないdry-runで、`--live` を明示した場合だけThreads APIへ接続します。

```bash
python3 scripts/run_due_post.py --now 2026-08-20T16:00:00+09:00
# 本番接続工程でのみ: python3 scripts/run_due_post.py --live
```

必要な環境変数（値はrepoへ保存しません）：

- `THREADS_ACCESS_TOKEN`
- `THREADS_USER_ID`

Threads APIは公式の `https://graph.threads.net` をversion pathなしで使用します。Instagram用の
`META_GRAPH_API_VERSION` はThreads URLへ適用しません。

Quizは問題画像付き親container作成・親publish・回答画像と短い回答文を持つIMAGE container作成・
`reply_to_id`付き回答publishの順です。問題・回答画像はInstagramと同一バイトの既存画像を使用し、
Threads専用画像は生成しません。親成功後に回答が失敗した場合は、`parent_status: posted`と
`parent_post_id`を保持し、`answer_status: failed`として区別します。NormalはTEXT containerを単独publishします。
成功receiptをqueue更新より先に保存し、二重投稿リスクを抑えます。

問題画像URLは公開repoのGitHub Raw HTTPSを `config/media_public.json` から生成します。live時は匿名HEAD取得を検査し、repoのprivate化、404、非HTTPSでは`BLOCKED_MEDIA_URL`で停止します。安全な一時的通信エラーだけ最大2回retryし、認証・データ・media URLエラーはretryしません。

### 分離された実接続テスト

`scripts/run_meta_connection_test.py` はproduction queueを読まず、`data/test_payloads/threads-quiz.json`だけを使用します。フラグなしは説明表示のみで、`--live-test`がある場合だけpreflight後にテスト親投稿と返信を投稿します。
実接続時はrepo rootの親にあるワークスペース共通 `.env` を読み込みます。シェルに既に設定された環境変数は `.env` で上書きしません。`.env` はGit管理対象外です。

```bash
python3 scripts/run_meta_connection_test.py
python3 scripts/run_meta_connection_test.py --live-test
```

preflightではUser IDとtokenをprofile GETで検証し、`threads_publishing_limit` の非破壊GETが成功することで
`threads_basic / threads_content_publish` を検証します。成功時の親・返信container IDとpost IDは
gitignoreされた`data/test_receipts/`へ保存し、access tokenは保存しません。
