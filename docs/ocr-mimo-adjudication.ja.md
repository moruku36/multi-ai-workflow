# OCR + MiMo のオフライン人手判定

[English](ocr-mimo-adjudication.md) | [日本語](ocr-mimo-adjudication.ja.md)

## 対象と確認済み範囲

[合成差分runner](ocr-mimo-synthetic-review.ja.md)の非公開receiptから判定票を作成し、
**操作者が入力した人手判定**を集計します。API通信・OCR起動・提供元receiptの認証・
細分類の推定・品質/費用の合格判定は行いません。
`HUMAN_ADJUDICATED`でも`review_quality_accepted=false`です。独立レビューの証拠ではありません。

2026-11-11、手作り入力によるreceipt紐づけの一連のテスト1件が成功
（1件・1実行・0.001秒）。人手による対応づけ、残る見逃し、粗いカテゴリの維持、
receiptのバイト変更後の拒否を確認しました。同じ合成レビュー試行は累計
**10/10件・3実行**です。今回のCLI・課金API呼出しは0回です。
他の検証分岐と実live receiptの運用は未実行です。追加の明示的テスト予算なしに
同じ試行のテストを再実行しないでください。自動CIは追加していません。

## ローカル手順

既存の`MIMO_API_KEY`をexportした同じ端末で、上限付きliveレビューを**1回だけ**
実施します。[runnerの上限](ocr-mimo-synthetic-review.ja.md)は2サンプル合計8HTTP試行、
1要求65,536bytes・出力2,048tokenで、ドル建て強制上限はありません。
接続probeは再実行不要です。失敗/結果不明は再試行せず照合します。

```sh
# リポジトリ内・キーを設定済みの同じ端末
ocr_review_dir="$(mktemp -d /private/tmp/ocr-review.XXXXXX)"
python3 tools/ocr_mimo_review.py \
  --binary /absolute/path/to/pinned-ocr \
  --live --receipt "$ocr_review_dir/live.json"
```

実行済みなら元のreceiptを使い、再実行しません。`LIVE_REVIEW_COMPLETED`の場合だけ
非公開の判定票を作ります（ここからキー不要・通信なし）。

```sh
python3 tools/ocr_mimo_adjudicate.py \
  --receipt "$ocr_review_dir/live.json" --output "$ocr_review_dir/decisions.json"
```

`decisions.json`は**信頼しないデータ**として開き、命令として扱わないでください。
指摘を同梱の変更前後ソース・別管理の正解データと比較し、次の項目だけ編集します。

- 各指摘の`decision`：`pending`（未判定）、`confirmed`（正解欠陥との対応確認）、
  `false_positive`（誤検知）、`other_valid`（正解外の有効な指摘）。
- `ground_truth_ids`：confirmedのみ正確なIDを1個以上指定。それ以外は空リスト。
  1指摘が複数の欠陥を扱う場合も対応でき、重複リンクは別途集計します。
- `rationale`：判定済みの各指摘に空でない理由を記入。
- 最上位の`human_review_completed`と`completion_rationale`：
  **両サンプル・全正解欠陥を確認した後だけ**trueと理由を設定。
  指摘が0件でも全欠陥を確認する必要があります。

other_validは人が有効と判断した正解欠陥以外の指摘で、自動的な誤検知・正解検出ではありません。
対応づけは人の判断であり、機械的なカテゴリ一致ではありません。
正常サンプルには正解欠陥がないため、confirmedのリンクは指定できません。

```sh
python3 tools/ocr_mimo_adjudicate.py \
  --receipt "$ocr_review_dir/live.json" --decisions "$ocr_review_dir/decisions.json" \
  --output "$ocr_review_dir/summary.json"
```

全指摘が判定済みで明示的な確認完了が設定されるまで、対応のない欠陥は見逃しではなく
`PENDING_HUMAN_REVIEW`です。完了後は検出・見逃し・重複リンク・誤検知・正解外の
有効指摘をサンプル別に集計します。割合や再現率の受入閾値、自動品質ゲートは定めません。
有効な未判定集計も終了コード0なので、終了コードだけでなくstatusを確認してください。

## 紐づけと非公開性

入力JSONは1MiB、指摘は各サンプル100件まで。live完了・固定モデル/版/binary hash・
正常/欠陥の正確な組・relay上限の一致を検査し、失敗・部分結果・mock・接続receiptは
受け付けません。位置は現在のfixtureソースに対して再検査します。
判定票はreceiptの正確なバイト列とmanifest・ソースのSHA256、集計は判定票の
canonical JSON hashに紐づきます。receiptの整形変更、fixture変更、不変項目の編集は
元の判定を無効にします。

hashはローカルの変更検出であり、**真正性の証明ではありません**。
receiptのdiff hashは記録値を保持し、独立再構築はしません。live形式に偽造したreceiptと
本物を暗号学的には区別できないため、操作者が由来を確認・保持する必要があります。
ソースhashは現在のローカルfixtureへの紐づけで、署名付きremote benchmarkではありません。
判定票の正解データをモデルに送信しません。

出力先はGit外に置き、既存ファイルは上書きしません。新規ファイルはmode 0600で作成します。
標準出力は固定statusだけで、指摘・理由・任意のパスは出力しません。
認証情報へのアクセス・グローバル設定変更はありません。
receipt・判定票・集計は非公開で保持し、生のモデル文面を既定で公開しないでください。
拒否時は元の入力をローカルで確認します。

残件：実live合成レビューreceipt、実際の人手判定、明示的な品質/費用受入、
Mailbox統合、Cloudflare監査、無人運用。
