# Alibaba＋Cloudflare手法の自動PRレビュー

[English](automatic-dual-review.md)

## 現在の状態 — 2026-11-12

実装はmainへ入り、このリポジトリのPRレビューは有効化済みです。
[限定的な疎通用実行](https://github.com/moruku36/multi-ai-workflow/actions/runs/43008525402)は
成功しましたが、その後の[#49](https://github.com/moruku36/multi-ai-workflow/pull/49)・
[#50](https://github.com/moruku36/multi-ai-workflow/pull/50)のレビューは
`INCOMPLETE`、両laneとも`FAILED_OR_UNKNOWN`でした。
これらのPRをマージしても、失敗が成功の根拠に変わるわけではありません。
[中央レビューhub](central-review-hub.ja.md)の両configゲートもfalseのままです。

## 動作

有効化時はmain向けPRの作成・更新・再オープン・Ready化で、次の2系統を起動します。

1. 固定版Alibaba OpenCodeReview v1.13.7＋MiMo mimo-v2.6-pro。
   既存の上限制御relayを使い、モデルのツールは結果登録と終了だけに限定します。
2. 固定版Cloudflare security-auditのSKILL・ATTACK-CLASSES・
   VALIDATION-AND-REPORTINGを読み込む別のMiMoレビュー役。
   OSSのguidance modeを実行します。全6段階監査・独立検証役・コード実行はありません。

合成サンプルではなく、実PRのmerge-base/head差分を使用します。
両方ともXiaomi/MiMoなので、異なる手法であり別providerの独立レビューではありません。
元差分hashと固定SHAを記録。Alibabaには変更された通常テキストのbefore/afterを
一時Gitリポジトリに再構成して渡します。コミットmetadata・未変更コードは対象外です。
削除だけの変更・実行権限変更・binary・symlink・submoduleなどは未対応として
失敗し得ます。最大20パス、元差分64KiB、before/after合計64KiBです。

## 設定と再確認

新規導入時は以下の手順を使います。このリポジトリではマージ・PR起動の有効化は
済んでいますが、一般的な実運用の受入は残っています。

1. 実装をレビューしてmainへマージします。信頼済みbase側を動かすため、
   導入PR自身では新workflowの自己検証はできません。
2. GitHub Settings → Secrets and variables → Actionsで既存キーを
   MIMO_API_KEY Secretとして設定します。コードには保存しません。
3. 下記の継続呼出し上限を確認し、repository variable
   DUAL_REVIEW_ENABLED=trueを設定します。この手順の記載で設定・認証は変更しません。
4. 小さいPRを作成／更新し、固定headの両系統receiptを確認します。
   1回の疎通用実行の成功だけで、一般的な対応範囲や後続の失敗からの復旧を証明しません。

有効化・Secret不足は明示的に失敗します。forkはソース入力としてのみ読み、
forkのスクリプトをSecret付きで実行しません。main以外のPR・ローカル未コミット変更は
対象外です。schedule・push起動・自動マージは追加しません。

## 呼出し上限と再試行

1イベントにつきAlibabaは失敗込み最大8HTTP、1要求64KiB・出力2,048tokens、
Cloudflareは最大1HTTP、1要求192KiB・出力2,048tokensです。
provider timeout 30秒、Alibaba process 150秒、job全体8分。
上流への自動再試行・redirect追従はありません。
ドル建て強制上限・日次累積課金上限はありません。有効化は継続課金の開始です。
金額上限はprovider側でも設定してください。停止はDUAL_REVIEW_ENABLED=falseです。

モデル呼出し前にcheck-runで実行予約し、repository単位のconcurrencyで直列化。
同じbase-tip/headは失敗・rerunを含め自動再実行しません。
予約応答喪失・中断・結果不明は人による照合が必要です。予約を消して再試行しないでください。
新しいhead/baseは別の課金対象です。GitHubのconcurrency仕様により連続更新時の
pending jobが置き換わる場合があるため、全ての瞬間的commitではなく最新headが対象です。
baseブランチだけの移動では起動しません。PR更新で新しいbindingを取得します。

## 結果と境界

dual-review-receipt checkは、不完全・古い結果でfailure、
指摘／検証残件ありでaction_required、両系統完了かつ記録された指摘・残件なしでsuccess。
successでも品質合格・独立性確認・人手判定・マージ許可にはなりません。
実行不完了ならworkflow自身も失敗します。
JSON receiptは7日間のActions artifactへ保存を試みます。任意のモデル本文は
CIログやコメントに出しません。artifactはrepositoryのActions公開範囲に従います。
私的なローカル報告を送信しません。branch protectionは変更しません。

controller・skill・依存コードは信頼済みmainのbase SHAから使用し、
PRはGit object APIで読み取るだけです。PRコード・hooks・custom tools・
依存インストール・tests・buildは実行しません。
provider keyは親processだけに保持し、CLIには使い捨てloopback tokenと
allowlist環境だけを渡します。モデルからのファイル探索ツールは無効です。

## 検証状態

先行するオフライン4ケースは成功しています。対象は実差分抽出、非対応入力拒否、
固定CLIのloopback経路、重複・結果不明の予約停止です。
中央コントローラーには、別にmockを使ったオフライン5ケースの成功があります。
いずれも実providerの品質やリポジトリ間の永続化の証明ではなく、この文書更新のための
再実行もしていません。

上記の疎通用実行はhead
`5606fbdc13025ed6b816470f6c64d0419f7ce7e4`で成功しました。その後の
[本体](https://github.com/moruku36/multi-ai-workflow/actions/runs/43075852872)と
[workflow・手順](https://github.com/moruku36/multi-ai-workflow/actions/runs/43075924119)の
実行は、それぞれの固定headで失敗しました。失敗laneのreceiptだけでは、
正確な原因・HTTP実数・実課金額は分かりません。費用ゼロと推測したり、予約済みの組を
再送したりしないでください。既存Alibaba adapterのMarkdown未対応もmain上では未解消です。

次は失敗receiptを保全し、実際の失敗原因を診断して、修正のレビュー・検証と現在revisionの
限定的な受入を行います。中央の定期実行は、別の方針確認と実連携受入を満たすまで
無効のままにします。
