# 中央レビュー hub

[English](central-review-hub.md)

[2026-11-12のソース限定草案](bounded-hub-draft.ja.md)は、権限不足時に拒否する
one-shot準備を追加します。定期実行やlive課金権限は有効化しません。

**無効状態の草案で、証拠はローカルのものだけです。** 以前のmockを使った5ケースは
1回の実行ですべて成功したと報告されており、再実行していません。その後の修正用mock
3ケースは **3 PASS／1 invocation／0.005秒** と報告されています。今回のreadiness変更では
再実行しておらず、live受入ではありません。
workflowと実連携の実PR受入は未実施です。[中央config](../config/central-review-hub.json)の
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
4. 人によるマージ後、レビュー済みの信頼するrevisionで、制限した新しい実対象PRを
   1件受け入れるための**新たな有料実行許可を明示的に取得**します。先に消費済み予約を
   照合し、未予約の新しい固定base/head/diff bindingを使います。20 path、差分65,536 byte、
   before＋after blob合計65,536 byteの既存上限を守ります。超過はblockedのままとし、
   上限の引上げやpath省略をしません。実ソースで両laneを完了し、実際のprovider/modelを
   記録し、指摘解消・独立性・人の受入ゲートを満たします。継続実行は無効のままです。
   そのゲートを無効にしたまま使える、別途レビュー済みの制限付き受入経路は、ここでは
   確立していません。経路が用意されるまではblockedです。呼出し側flagやローカル証拠で
   経路不足を回避したり課金を承認したりできません。
5. 最終的な対象Check／receiptとhub予約／台帳を読み戻します。正確な現在の
   base/head/diff、完了と安全な診断、消費済みの失敗・不明記録の保持、hub revisionを
   またぐ永続的な重複排除を確認し、その読戻しを明示的に受け入れます。mockや成功Check
   だけでは受入になりません。予約済みの組を再送したりmarkerを削除したりしません。
6. 受入後に初めて、**その時点の現在のUTC時刻**を意図して選び、`CENTRAL_REVIEW_SINCE`へ
   厳密な`YYYY-MM-DDTHH:MM:SSZ`形式で設定します。過去のcutoffを再利用したり、受入用PRや
   backlogを含めるために遡らせたり、過去の処理を再実行したりしません。正確なcutoffを
   読み戻した後、`CENTRAL_REVIEW_ENABLED`を正確に`true`へ設定して読み戻します。
   configの両ゲート、新しい実PR／台帳証拠の受入、最後の実行時ゲートは別々の要件です。
   それまでは実行時variableを未設定か`false`にします。

## 探索と実行

草案のworkflowは30分ごとのscheduleと、入力項目のない手動dispatchを定義しています。
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
返却・自動retry・自動照合・修正後の再送はありません。書込み応答を失った場合は
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

2026-11-12の今回の草案より前は、Alibaba adapterの未対応Markdown処理を未解消と
記録していました。失敗laneも予約を消費します。この過去の観測は、個別の失敗実行の
原因診断ではありません。実PR受入、GitHubでの永続化動作、App installation範囲、
full fetchの資源制御は引き続き未検証です。

## 静的修正 — 2026-11-12

ローカルの固定OCRソース
`b1dcffb0729f3f2e3e47170968a5014a2e035580`（v1.13.7）を読取り専用で確認しました。
[flag定義](https://github.com/alibaba/open-code-review/blob/b1dcffb0729f3f2e3e47170968a5014a2e035580/cmd/opencodereview/shared_flags.go)は
`--rule`をサポートし、`--no-filter`は指摘の後処理だけに作用してファイル選択には
影響しません。[rule loader](https://github.com/alibaba/open-code-review/blob/b1dcffb0729f3f2e3e47170968a5014a2e035580/internal/config/rules/system_rules.go)は
`include` globを受け付けます。adapterは信頼するscratchの、ソースsnapshotの**外側**に
`{"include":["**/*.md"]}`だけのruleファイルを作り、`--rule`で渡すようにしました。
対象由来の方針やレビュー指示文は加えません。
[選択処理](https://github.com/alibaba/open-code-review/blob/b1dcffb0729f3f2e3e47170968a5014a2e035580/internal/agent/selection.go)では
binary・秘密情報pathの拒否がincludeより先に行われ、削除・サイズのゲートも残ります。
他の拡張子には既定の選択規則が残ります。snapshot全ファイル数のcoverage、期待するmodel、
完了応答・出力、警告なし、有効な指摘は引き続き必須で、選択の配線だけでは完了を証明しません。

両adapterは、固定語彙の停止stageを持つ型付きの失敗を返すようにしました。
中央の失敗receiptには、そのstage、CLI終了code（−255～255の整数、それ以外は`null`）、
HTTP試行数・完了応答数（Alibabaは0～8、手法laneは0～1、それ以外は`unknown`）、
booleanのhalted状態または`unknown`、安全なusageだけを保持します。usageは
`prompt_tokens`・`completion_tokens`・`total_tokens`のみで、各値は0～1,000,000,000の
整数または`unknown`、行数はそれぞれ最大8／1です。usage欠落は`unknown`で、行がないことは
費用ゼロを意味しません。Alibabaのcounterはrelay cleanup後に取得し、workerが未停止・
応答不明ならcounterも不明です。一般の例外には不明のmetadataを使い、ゼロを作りません。
workerとreceipt書込み側でこのallowlistに再投影し、例外文・path・stderr・provider文・
認証情報・headerは診断から除外します。stageは停止箇所であり、根本原因ではありません。
中央の完了receiptにも範囲を制限した完了数・halted・終了metadataを保持します。

[`tests/check_central_review_live_acceptance.py`](../tests/check_central_review_live_acceptance.py)に
mockケースを正確に3つ作成しました。名前は`test_trusted_markdown_rule_wiring`、
`test_safe_alibaba_failure_diagnostics`、`test_central_failed_receipt_persists_safe_metadata`です。
初回の静的修正時点では**いずれも未実行でした**。その後に記録されたmock結果は
**3 PASS／1 invocation／0.005秒**であり、実providerや実PRの受入ではありません。
以前の中央5ケースはAPI・source・lane・preflightをmock化した過去の証拠のままです。
今回のreadiness変更では再実行していません。ケース作成は実行予算を増やしません。
workflow・config・auth・settings・hook、有効化は変更していません。

残る受入には、別途承認された評価、今回の修正のcurrent headでの外部レビュー、指摘解消、
信頼するbaseへの導入が必要です。制限した実PRで、同じ固定base/head/diff bindingに対する
**両laneの実ソースでの完了**と、実際のprovider/model記録を示す必要があります。
最終的な対象Checkとhub予約をChecksから読み戻し、正確な現在のbindingと保持した診断を確認し、
hub台帳と対象receiptの両方で永続的な重複排除を確立します。hub revisionをまたぐ失敗・不明の
組も対象です。新たな有料処理前に消費済み予約を照合し、予約済みの組を再送したりmarkerを
削除したりしないでください。mock・静的確認・成功Checkだけではゲートを満たしません。
通常の[2系統レビュー契約](dual-review.ja.md)、必要な別providerの独立性、人の受入、
mergeゲートも残り、中央の継続実行は無効のままです。

## 継続開始前のオフラインreadiness — 2026-11-12

[`tools/central_review_readiness.py`](../tools/central_review_readiness.py)は、呼出し側flagを
受け付けない読取り専用のオフラインreporterです。固定したローカルの中央config／workflowと、
`origin/main`・`HEAD`から固定したmerge-base/headの、制限付きローカルGit metadata／差分だけを
読みます。fetch・認証情報の読取り・reviewer呼出し・ファイル書込み・ゲート変更は行いません。
remote-tracking refは古い可能性があり、未commitの編集や最新の対象PR状態は計測対象外です。

変更path数、差分byte数、before＋after blobの合計サイズを、固定上限の
**20 path／差分65,536 byte／snapshot合計65,536 byte**に対して報告します。
超過・ref欠落・未対応blob・制限付き読取りの失敗はblockedのままです。計測不能な値は
`null`とし、差分の打切り時には下限を示します。20 path超過時はblob合計の走査をしません。
除外や上限overrideはありません。サイズ上限内というローカル観測は、完全なsource preflight・
merge承認・課金許可・対象受入・有効化権限を意味しません。

reportは、観測したconfig値に関わらず、**人のmerge**、**新たな有料実行許可**、
**新しい実PRのCheck／台帳受入**、**runtime enable**を別々の外部証拠待ちstageとして保持します。
[`tests/check_central_review_readiness.py`](../tests/check_central_review_readiness.py)には
オフラインケースを2つ作成し、**実行していません**。読取り専用reporterを1回呼び出し、
ローカルの`origin/main`／merge-base `7eabdf4973fdf06f768319020a60311275d6b7b2`から
`HEAD` `8e53c1e79de5f6ce690cc8a72072f974b3857acd`について、**5 path、差分54,178 byte、
before＋after blob合計170,398 byte**を観測しました。snapshot上限により、この入力は
**BLOCKED**のままです。上限や除外は変更していません。この観測は現在の未commit修正を
含まず、テストや新しい実対象の受入でもありません。必要なcurrent headの2系統レビューも
未実行で、外部経路や新たな有料実行許可を使っていません。
上記の順序による有効化は引き続き未実施です。
