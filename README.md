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
