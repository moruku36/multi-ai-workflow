# OpenCodeReview + MiMoによる合成差分レビュー

[English](ocr-mimo-synthetic-review.md) | [日本語](ocr-mimo-synthetic-review.ja.md)

## 確認できた段階

固定版Alibaba OpenCodeReview v1.13.7を、接続試験の `llm test` ではなく `review` で起動します。正常／欠陥入りの同梱ソースを、それぞれ新しい一時Gitリポジトリの変更前後として配置します。正解manifest・模擬レビューJSON・作業プロジェクトのコードはコピーも送信もしません。実際のGit差分のSHA256を各サンプルに記録します。

実CLI＋ループバック模擬レビューを含む選択4件が1回の実行で成功（0.875秒）。先の接続試験5件と合わせ、同じ試行の実行済みは**9/10件・2回のテスト起動**です。自動CIの追加・今回の有料API呼出しはありません。

以前の実接続は、操作者報告のreceiptでMiMo応答2回とツール往復を確認したものです。コードレビューの証拠とは別です。エージェントは操作者のAPIキーを受領・保存していません。**実MiMoによる合成差分レビューと品質受入は未完了です。**

## 実行

追加Python依存はありません。[接続準備](ocr-mimo-standalone.ja.md)と同じ固定版バイナリを使います。

```sh
# 既定は実CLI＋ローカル模擬応答。receiptは未作成のパス。
python3 tools/ocr_mimo_review.py --binary /absolute/path/to/pinned-ocr --receipt /private/non-git-directory/new-mock-review.json

# 有料レビュー：MIMO_API_KEYを既にexportした同じターミナルで実行。
python3 tools/ocr_mimo_review.py --binary /absolute/path/to/pinned-ocr --live --receipt /private/non-git-directory/new-live-review.json
```

下記上限を受け入れた上でliveは1回だけ実行します。接続試験は再実行しません。中断・FAILED_OR_UNKNOWN時は再送せず結果照合が必要です。receiptは排他的に0600で作成し、実行前に結果不明状態をfsyncします。指摘本文は非公開receiptにだけ残し、端末出力・公開はしません。

実キーは親relayのみで保持し、CLIへは一時ループバックtokenだけを渡します。HOMEの変更・グローバル設定の編集はしません。既存OCR設定・グローバルruleファイルがある場合は照合待ちで停止します。一時Gitの処理は操作者／システム設定を継承せず、合成baseline commitのhook・署名を無効にします。上流CLIは通常のOCRセッション保存先に合成レビュー記録を保存する場合があります。runnerはこれを削除しません。

## 実行上限（ドル上限ではありません）

- 固定モデル `mimo-v2.6-pro`、固定endpoint `https://api.xiaomimimo.com/v1/chat/completions`。
- planner・tool往復・失敗・結果不明を含め、**両サンプル合計でHTTP試行最大8回**。
- 1リクエスト65,536 body bytes、出力指定2,048token、HTTP timeout 30秒。CLIは各サンプル150秒まで。
- 並列数1、low effort、後処理filter呼出しなし。実通信は再送・redirect・別モデル／endpointへの切替なし。
- 通信／検証失敗で以後の通信と残りサンプルを停止。終了コード0だけでなく、同一モデルの応答実績・レビュー対象1ファイル・complete/success JSON・警告なし・妥当な指摘位置が必要。
- byte上限は厳密な入力token上限ではありません。**ドル建て強制上限は未実装**で、請求額はunknownです。2026-11-11確認の海外cache-miss公開料金（入力$0.435/M・出力$0.87/M）では実使用量に依存します。以前の接続試験2回とは異なる上限です。
- 指摘0件の完了は有効な実行結果ですが、欠陥がない証明ではありません。

## 結果と残作業

OCRの `security`・`bug` 等はそのまま保存し、`security/path_traversal` 等の細分類へ推測変換しません。既存mock専用scorerは変更せず、実結果をmockと偽って投入しません。誤検出・見逃し・細分類一致は自動受入せず、別の正解データとローカルで照合してください。常に `review_quality_accepted=false` です。

次は操作者による上限付き実レビュー、その後に正常サンプルの誤検出と欠陥4件の人手判定です。細分類の機械採点・品質／費用の明示受入・Mailbox連携・Cloudflare監査・無人運用は未完了です。

選択検証：

```sh
python3 tests/check_ocr_mimo_review.py --binary /absolute/path/to/pinned-ocr
```

同じ試行では残り1/10件なので、予算増加なしに4件を再実行しないでください。
