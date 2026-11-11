# 中央レビュー hub

[English](central-review-hub.md)

**無効状態の草案で、オフライン検証は成功しています。** mockを使った5ケースは
1回の実行ですべて成功しました。workflowと実連携の実PR受入は未実施です。[中央config](../config/central-review-hub.json)の
`enabled`と`paid_execution_authorized`は現在どちらも`false`です。
これらのファイルは、自動稼働やレビュー品質の受入を証明しません。

## 中央で一度だけ行う設定

1. GitHub Appのrepository権限を **Contents: read**、**Pull requests: read**、
   **Checks: read and write** にします。GitHub必須のMetadata readも付与されます。
   Actions・管理・ソース書込み権限は不要です。設定済みownerに、hubを含む
   **All repositories** でインストールします。同じinstallationの現在・将来の
   リポジトリが対象です。探索ではprivateを除外しますが、token自体はinstallationの
   privateにもアクセスできるため、hubとApp秘密鍵を保護してください。
2. hubだけにActions variable `APP_ID`とsecret `APP_PRIVATE_KEY`を設定します。
   既存secret `MIMO_API_KEY`もhubだけに保持します。対象ごとのworkflow・鍵・設定・
   コード方針の変更は不要です。固定したApp-token actionにはownerを渡し、
   `repositories`を意図的に省略してinstallation全体を探索できるようにします。
   Contents read・Pull requests read・Checks writeを明示的に要求します。
   `GITHUB_TOKEN`はContents readのみで、リポジトリ間の書込みはApp tokenが担います。
3. 信頼するworkflow・controller・config、全リポジトリへのアクセス、providerへの
   ソース開示、予約上限、継続的な有料実行について、中央で一度コード・方針レビューを
   完了します。指摘を解消し、既存のレビュー・受入ゲートを満たします。その中央変更で
   有料実行を明示承認し、**`enabled: true`と`paid_execution_authorized: true`の両方**を
   設定し、既存の人によるゲートを経て信頼する`main`へマージします。
   これは将来の有効化手順であり、草案そのものによる承認ではありません。
4. hub variable `CENTRAL_REVIEW_SINCE`に、有効化の起点を厳密なUTC形式
   `YYYY-MM-DDTHH:MM:SSZ`で設定します。現在以前の時刻が必要です。その後hub variable
   `CENTRAL_REVIEW_ENABLED`を正確に`true`にします。configの両ゲート・有効なcutoff・
   実行時ゲートがすべて必要です。有効化が受け入れられるまでは未設定か`false`にします。

## 探索と実行

workflowは30分ごとのscheduleと、入力項目のない手動dispatchだけを受け付けます。
jobは設定済みhub・`refs/heads/main`・実行時有効化variableを要求し、固定した
`github.sha`をcheckoutします。任意の手動source refはありません。
`central-review-hub`の単一concurrency groupでキャンセルせず直列化し、
Ubuntu 24.04上でjob timeoutは20分です。

installation内のリポジトリとopen PRを探索し、hub・private・fork・archived・disabled・
別ownerのリポジトリ、draft PR、forkまたは削除済みhead、対象のdefault branch以外を
baseとするPRを除外します。PRの`updated_at`はcutoffより**厳密に後**である必要が
あります。open PRを走査してから`updated_at`で絞り込み、過去のbacklogのレビュー処理は
行いません。有効化以前または同時刻が最終更新のPRは除外します。
作成が古いPRでも有効化後に更新されれば対象になり得ます。過去を再処理するために
cutoffを戻さないでください。全リポジトリinstallation内の新しい適格リポジトリにも
対象ごとの設定は不要です。

現在のdefault branch先端とPR headを再確認します。両laneには同じ固定merge-base/headの
ソース差分を渡し、receiptには探索時のbase先端とdiff hashも結び付けます。
対象のcheckout・build・依存導入・hook・test・PRコード実行は行わず、blobを調べます。
Alibaba OpenCodeReview v1.13.7はHTTPSで取得しSHA-256を確認し、信頼するソース専用の
足場を使います。隠しpath要素、`opencodereview`を含む要素、`config.json`/`rule.json`
の制御pathは黙って省略せず拒否します。global OCR制御ファイルもpreflightを停止させます。
対象workflowや鍵はコピーしません。

reviewerに渡すのは制限付きのソース・差分入力だけです。Actionsでのソース・artifact
アップロードや、生のソース・providerログの保存は行いません。対象Checksには長さを
制限しエスケープした未信頼の指摘抜粋、hub consoleには集計statusだけを出します。
運用会話・認証情報・アカウント証拠を公開しないでください。

## 予約と保持する状態

現在の上限は、対象やhubソースのrevisionをまたいで **1実行2 PR予約、UTC日次6予約**です。
ソース収集の前に、固定hub anchor commitのChecksへ追記専用の予約を書いて読み戻し、
対象receiptも書いて読み戻します。各laneのunknown markerも呼出し前に読み戻します。
anchorと完全なcheck台帳を保持してください。読取り不能・不正・anchor欠落・
打切り状態では有料処理を止めます。

失敗・中断・結果不明も含め、すべての予約が枠を消費します。ソースコンテキスト開始・抽出の
失敗は`SOURCE_BLOCKED_OR_UNKNOWN`の失敗receiptを対象に記録し、予約枠を消費して
laneを呼びません。次の適格候補へ進み、以後のpollでは同じ組を除外して、同じ候補の
失敗によって後続が毎回止まることを防ぎます。台帳・receiptの書込みや読取りが不確かな
場合は、実行全体を引き続き停止します。日次集計は全statusを含み、
日付境界ではCheck開始日と予約日の両方に保守的に算入します。前日の予約を使って翌UTC日に
laneを開始することはできません。重複排除は対象repository・
base先端・headと対象receiptで行い、hub checkout SHAには依存しません。
返却・自動retry・自動照合・Markdown修復はありません。書込み応答を失った場合は
実行を停止します。枠を回復するためにcheckを削除しないでください。

予約PRごとに **Alibaba最大8 HTTP試行＋Cloudflare手法最大1 HTTP試行**を許し、
Xiaomi `mimo-v2.6-pro`で順番に実行します。これはリクエスト数と予約数の上限であり、
**金額上限ではありません**。token使用量・課金・不明な応答も考慮が必要です。
Cloudflareは手法の提供元で、モデルproviderではありません。同じprovider/modelの
2 laneは独立性を証明しません。指摘解消・必要な別providerの証拠・人によるmerge権限が
引き続き必要です。`BOTH_RECORDED_NOT_ACCEPTED`や成功Checkもmergeを承認しません。
bindingが変わった場合や確認不能の場合、receiptは失敗扱いになります。

## 制限・停止方法・残る未検証事項

探索上限はinstallationの250リポジトリ、各リポジトリの100 open PRです。
hub台帳と対象ごとの該当receiptは各1,000件が上限です。不完全なpaginationや上限超過は
追加の有料処理前にfail closedします。既存のソース抽出制限である20 path、64 KiBの
diff・snapshot上限、通常ファイル制限、binary・symlink拒否を維持します。
Git full fetchは両commitから到達できる全履歴・blobを取得し得ます。
**256 MiBはscratch diskの観測上限であり、通信量・diskの厳密な上限ではありません。**
監視間隔中にpackが超過し得ます。厳密な制限にはrunner側のdisk・network制御が必要で、
ここには実装していません。時間・出力制限では代替できません。

以降の処理を止めるにはhubの`CENTRAL_REVIEW_ENABLED`を`false`にします。
コード方針として継続的に止める場合は中央レビューを経てconfigの両ゲートを`false`へ
戻します。実行中jobは開始時の環境を保持するため、variableの無効化で中断はされません。
課金され得るlaneのキャンセルは避けてください。中断結果は不明のまま予約を消費します。
停止・再開時もreceipt・台帳を保持します。再開には受入済みの方針と意図したcutoffが必要で、
過去の再処理は行いません。

既存Alibaba adapterの未対応Markdown処理は**未修正のまま**です。該当laneは失敗し、
予約を消費し得ます。5つのオフラインケースはAPI・source・lane・preflightをすべてmock化して
実行して成功しましたが、実provider実行や実連携の受入を証明しません。実PR受入、GitHubでの永続化動作、
App installation範囲、full fetchの資源制御は未検証です。通常の
[2系統レビュー契約](dual-review.ja.md)と人・独立性・mergeのゲートも引き続き適用されます。
