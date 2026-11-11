# Alibaba＋Cloudflare手法の自動PRレビュー

[English](automatic-dual-review.md)

## 動作

mainへのマージ・有効化後、main向けPRの作成・更新・再オープン・Ready化で、
次の2系統を起動します。

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

## 有効化（まだ実施していません）

1. 実装をレビューしてmainへマージします。信頼済みbase側を動かすため、
   導入PR自身では新workflowの自己検証はできません。
2. GitHub Settings → Secrets and variables → Actionsで既存キーを
   MIMO_API_KEY Secretとして設定します。コードには保存しません。
3. 下記の継続呼出し上限を確認し、repository variable
   DUAL_REVIEW_ENABLED=trueを設定します。本PRでは設定・認証を変更しません。
4. 小さいPRを作成／更新し、固定headの両系統receiptを確認します。
   この実環境受入は未実施です。

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

実装とソース確認までです。同じ開発試行の承認枠は13/13件・4回実行で消化済み。
追加test・CI dispatch・新規実課金レビュー・Secret設定はしていません。
次の提案はoffline 4件（実差分抽出、非対応入力拒否、実CLIのloopback経路、
重複／結果不明の予約停止）、有効化後に別枠の実PR受入1回です。
