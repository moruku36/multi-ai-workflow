# クラウドアクセスガイド: 読み取り専用の請求・メタデータ確認(Windows、CLI優先)

English: [05-cloud-access-readonly.md](05-cloud-access-readonly.md) | 日本語: [05-cloud-access-readonly.ja.md](05-cloud-access-readonly.ja.md)

本書はドキュメントのみです。クラウド操作を承認するものではなく、作成時にも何も実行していません。ルーティングポリシーは変更しません。PRやマージの人間による承認は、クラウド操作の承認にはなりません。

## 目的と原則

- クラウドのプリンシパルを認証するのはCLIです。AIは、承認された範囲を限定した操作を調整・実行します。モデルのサブスクリプションはクラウドIAMではありません。
- オーナーが許可した場合に限り、各AIは既存のローカル認証済みCLIセッションを共用できます。モデル間・ホスト間・ファイル間・リポジトリ間で認証情報をコピーしてはいけません。
- 主ホストはWindowsです。まずCLIを使います。CLIで請求情報が取得できない、または課金が発生する場合に限り、認証済みの既存Chrome GUIをフォールバックとして使います。
- アクセス可能と主張する前に、インストール済みCLIのバージョン、対応コマンド、アカウントスコープを確認します。
- インストールや新規ログインは、実行時の承認なしには行いません。

## 承認スコープ

このリポジトリの外で管理する、厳密な非公開許可リストを使います。内容は、オーナーが確認済みのAWSアカウント・プロファイル・リージョン、Azureサブスクリプション、GCP請求アカウントとプロジェクトです。社内・不明なスコープは除外します。

- AWS: リージョン単位の観測結果は、全サービス・全リージョンを網羅しません。
- Azure: 必ず明示的に`--subscription`を指定します。`az account set`は実行しません。
- GCP: 必ず明示的にプロジェクトを指定します。

## 読み取り専用コマンド(汎用例)

あくまで例です。プレースホルダーは非公開許可リストの値で置き換えます。
リソースや料金を読む前に、返されたアカウント・サブスクリプション・請求先とプロジェクトの対応を許可リストと照合します。メタデータの出力は非公開で扱い、引き継ぎや公開の前に識別子・ARN・メールアドレスを伏せます。

```
aws --version
aws sts get-caller-identity --profile "<PROFILE>" --region "<REGION>"
az account show --subscription "<SUBSCRIPTION_ID>"
gcloud --version
gcloud billing accounts describe "<BILLING_ACCOUNT_ID>" --project "<PROJECT_ID>"
gcloud billing projects describe "<PROJECT_ID>" --project "<PROJECT_ID>"
```

認証情報、トークン、デバッグ情報を出力するコマンドは実行しません。拡張機能の自動インストールやAPIの自動有効化が起こりうるコマンドも実行しません。

## 請求の証跡

- AWS: 無料のBillsページ`https://console.aws.amazon.com/billing/home#/bills`を使います。Cost Explorer APIはプライマリビュー1リクエストあたり$0.01のため、別途支出上限が承認されない限り避けます。ダッシュボード操作でCost Explorer、アドオン、異常検知モニターを有効化しないでください。
- Azure: Cost Management Queryは読み取り専用で、追加費用はありません。ActualCostは正味の支払額ではないため、クレジットと税は別途確認します。空の行やARMリソースがないことは、利用がない証明にはなりません。データ遅延は、EA/MCAで通常8〜24時間、PAYGで最大72時間です。
- GCP: `gcloud billing`はメタデータを返すだけで、日次の利用料金は取得できません。認証済みの既存Reportsページを使い、BigQueryのスキャンやエクスポートの有効化は行いません。データは通常1日以内に反映されますが、24時間を超えることもあります。

記録する項目: 実績と予測、総利用額・無料枠・クレジット・正味額、通貨、利用期間または請求期間とタイムゾーン、最終更新と遅延、日次・サービス別の内訳、正確なスコープ、ページネーション。正味額がゼロでも、利用がゼロであることや将来ゼロであることの証明にはなりません。本書は現在の残高を断定せず、オーナー申告の実際の料金も公開しません。

## 証跡カテゴリ

- **owner-reported(オーナー申告)**: オーナーが述べた内容で、独立した確認は未実施。
- **CLI-verified(CLI確認済み)**: 承認スコープ内のCLI呼び出しで得られた結果。
- **GUI-observed(GUI観測)**: 認証済みブラウザセッションで確認した内容。
- **incomplete(不完全)**: 一部のみ、古い、またはブロックされた情報。不足している点を明記します。

## トラブルシューティング

| 症状 | 対応 |
|---|---|
| CLIの権限・認証エラー | オーナーが行うべき最小限の手順を具体的に報告します。ログインやトークン作成は行いません。 |
| 承認ホストなしの`-p`/手動実行 | GUIの確認なしに`permission_denials`が記録されることがあります。通常の承認レビューを経た、呼び出しごとに名前を指定した読み取りツールは、保存される権限変更とは別物です。bypassPermissionsは使いません。 |
| 複数のブラウザデバイス | ユーザーが明示的に選んだWindowsデバイスに固定します。 |
| セッションのtabs_contextに既存のコンソールタブが出ない | サポートされている再利用方法を使うか、制限として報告します。タブID、セッションストア、非公開エンドポイントを推測してはいけません。 |
| サイト権限 | 別のレイヤーです。確認プロンプトは、実際に観測した場合のみ報告します。新規の許可には実行時の承認が必要です。見えないプロンプトを探し回らないでください。 |
| サインインへのリダイレクト | 全体のサインアウトの証明にはなりません。 |
| レンダラーの進捗表示やgstaticエラー | 料金ゼロの証明にはなりません。範囲を限定した通常の読み取りを行うか、実際に観測された承認済みの公開フォールバックURLを使います。ネットワーク・セキュリティ・ブラウザ設定は変更せず、スクリーンショット権限も付与済みと仮定しません。 |

## 読み取り専用の境界

リソースの作成・起動・停止・削除は行いません。予算、ポリシー、サブスクリプション、IAM、セキュリティ設定も変更しません。クラウドシェルのプロビジョニング、有料クエリ、自動スケジュールも行いません。永続的な新規認証、OAuth、APIキー、権限の追加には、別途承認が必要です。本ガイドは削除を承認するものではありません。

## 非公開ハンドオフテンプレート

記入済みのコピーやログは、公開リポジトリに置かないでください。

```
実行者 / プリンシパル: <NAME> / 検証状況: <verified|unverified>(秘密情報なし)
承認スコープ: <PROVIDER, ACCOUNT_ALIAS, REGION/PROJECT>
操作 / ツール: <OPERATION> / <TOOLS>
証跡カテゴリ: <owner-reported|CLI-verified|GUI-observed|incomplete>
期間 / 通貨 / 最終更新 / 遅延: <...>
総額 / クレジット / 正味: <...>
確認済みスコープ: <...>   アクセス不可のスコープ: <...>
オーナーの次のアクション: <...>
```

## 参考資料

- [AWS Cost Explorer pricing](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/pricing/)
- [AWS: viewing your bill](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/getting-viewing-bill.html)
- [aws sts get-caller-identity](https://docs.aws.amazon.com/cli/latest/reference/sts/get-caller-identity.html)
- [az account](https://learn.microsoft.com/en-us/cli/azure/account?view=azure-cli-latest)
- [Understand Cost Management data](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/understand-cost-mgt-data)
- [GCP billing reports](https://docs.cloud.google.com/billing/docs/how-to/reports)
- [gcloud billing accounts describe](https://docs.cloud.google.com/sdk/gcloud/reference/billing/accounts/describe)
- [gcloud billing projects describe](https://docs.cloud.google.com/sdk/gcloud/reference/billing/projects/describe)
- [Claude Code headless](https://code.claude.com/docs/en/headless)
- [Claude Code in Chrome](https://code.claude.com/docs/en/chrome)
