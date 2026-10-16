# Daybreak対象モデルと認可されたOSSセキュリティレビュー — 2026-10-16

[English](daybreak-authorized-oss-security-review.md) | [日本語](daybreak-authorized-oss-security-review.ja.md)

**状態：文書化のみ・未有効化。** 本ページは、OpenAIの公開文書がDaybreak（Trusted Access for Cyber）について述べている内容を記録し、アクセスが承認された場合に本プロジェクトが認可されたOSSセキュリティレビューをどう運用するかを提案します。**Daybreak BlueまたはRedのアクセスを保有しているとは主張せず、申請もしておらず、Daybreakのリクエストやスキャンも実行していません。** モデル名は本人の運用表記ではなく、出典に印字された表記のままです。実行時に使えることの証明ではありません。認証情報・リクエスト・設定・実行環境は変更していません。

## 1. 公式資料の記載

2026-10-16（UTC）にページを直接取得して確認しました。ページに公開日の表示はなく、変更され得るため、依拠する前に再確認してください。

| 項目 | 出典の記載 | 出典 |
|---|---|---|
| プログラム | Daybreakは、承認された利用者が認可された防御的サイバーセキュリティ作業を行うのを助けるもの。アクセスはTrusted Access for Cyberで申請する。これは「審査制のアクセスプログラムであり、モデル名ではない」。 | [Models and Trusted Access](https://learn.chatgpt.com/docs/cyber-safety)、[Cybersecurity checks](https://developers.openai.com/api/docs/guides/safety-checks/cybersecurity) |
| Blue | 認可された防御作業向けに、主力モデルの拒否を減らす：脆弱性の発見とトリアージ、セキュアコードレビューと脅威モデリング、検知エンジニアリングとインシデント対応、管理された環境でのマルウェア分析、修復とパッチ検証。ほとんどの防御担当者に推奨される出発点。 | Models and Trusted Access |
| Red | 別途承認される専門のサイバーモデル。管理された脆弱性再現、PoC・エクスプロイトの検証、ペネトレーションテスト、レッドチーム。日常のセキュリティ作業の既定の選択ではなく、Blueの承認はRedを与えない。 | Models and Trusted Access |
| 承認の範囲 | 承認は、特定の人またはサービス、ChatGPTワークスペースまたはAPI組織とプロジェクト、提供形態とモデル、利用画面に対して適用される。申請や本人確認は承認を保証しない。 | Models and Trusted Access、Cybersecurity checks |
| 企業での利用 | 承認されたワークスペースやプロジェクトは、組織の認可された内部作業にのみ使う。外部ユーザー、顧客、下流の機能へ広げない。不明なら止めて確認する。 | Models and Trusted Access |
| データ保持 | Trusted AccessはZero Data Retentionを自動では付与しない。 | Models and Trusted Access、Cybersecurity checks |
| 環境 | Trusted Accessは、環境の構成、承認された対象・行動の制限の強制、提案された行動のレビューを行わない。 | Models and Trusted Access |

### 1.1 Daybreakで使えるモデル（APIガイド）

[Use Daybreak in the Responses API](https://developers.openai.com/api/docs/guides/daybreak) より。リクエストの `access_programs.cyber` には `standard`、`daybreak_blue`、`daybreak_red` を指定し、モデルは `model` フィールドで選ぶ。

| モデルID | `access_programs.cyber` | ガイドの記載 |
|---|---|---|
| `gpt-6-sol` | `standard` または `daybreak_blue` | 主力モデル。Blueで承認済みの防御作業向け。`daybreak_red` は拒否される（`invalid_access_program`）。 |
| `gpt-6.1-sol`、`gpt-6-astra` | `daybreak_blue` | 拒否の削減。ガイドによれば、組織のDaybreak Red承認とプロジェクトのアクセス有効化が必要。どちらも `daybreak_red` は拒否。 |
| `gpt-5.6-cyber` | `daybreak_red` | 高度で認可された作業向けのサイバーモデル。Red承認が必要。 |

- リクエスト値は、承認されたアクセスの範囲内での挙動を選ぶもので、アクセスを付与しない。プロジェクトにプログラムとモデルの両方へのアクセスが必要。
- フィールド省略時：`gpt-6-sol` などの主力モデルは、アクセスがあればBlue扱い、なければ標準の安全策。`gpt-5.6-cyber` はRedが選ばれ、アクセスがなければ失敗する。
- エラー：`400 invalid_access_program`、`400 unsupported_access_program`、`403 access_program_not_enabled`。これとは別に、APIの安全策による `cyber_policy` エラーや一時的なアクセス制限があり得る（利用者ごとの `safety_identifier` で影響範囲を限定できる）。
- `-latest` エイリアスは承認されたアクセスにより解決先が変わり得る。返された `model` を確認する。
- 本リポジトリが限定的な定常作業に使うGPT-6 Luna は、読んだガイドに記載がない。LunaがDaybreak対象だと仮定しない。

### 1.2 出典間の名称の違い（未解決）

- Models and Trusted Accessのページは提供物を **GPT-Daybreak-Blue** と **GPT-Daybreak-Red** と呼ぶ。APIガイドは上記のモデルIDを使い、BlueとRedをアクセスプログラムとして扱う。
- 報道やXのOpenAI投稿は、Blueを「GPT-5.6 Sol」、Redを「GPT-5.6-Cyber」と説明する。APIガイドはBlue系に `gpt-6-sol`／`gpt-6.1-sol`、Redに `gpt-5.6-cyber` を挙げる。
- これらは照合できていない。APIガイドのモデルIDを作業上の基準とし、自分のプロジェクトのコンソールとエラーメッセージで確認する。

## 2. 認可されたOSSセキュリティレビュー — 運用手順案

本節は、上記の出典とCodex Securityおよび推奨構成の文書に基づく**本プロジェクトの提案**です。OpenAI公式の手順ではなく、各手順の効果は未測定です。

**「認可」の範囲。** 自分たちが所有するリポジトリ、または保守者が明示的にレビューに同意したもの（公開されたセキュリティポリシー、招待、調整されたプログラムなど）に限る。ソースが公開されていることは、稼働中の第三者システムを試験する認可ではない。レビューは静的解析または隔離したローカルコピーで行い、OSSプロジェクトや利用者の稼働中サービスには触れない。

1. **前提。** 承認された人またはサービス、API組織・プロジェクトまたはワークスペース、モデル、利用画面を書面で確認する（定常レビューはBlueのみ）。1つでも不明なら止める。定常レビューにRedを使わない。Redは別承認と具体的な理由が必要。
2. **開始前の境界記録**（推奨構成の項目）：対象リポジトリとリビジョン、除外システム（本番・無関係な基盤）、承認されたツールとサービス、許可・禁止する行動、開始・終了時刻とデータの扱い、開示と保守者との調整、停止条件と明示的な人の承認が要る行動。これをエージェントにタスク文脈として渡し、プロンプトとは独立に強制する。
3. **環境。** 秘密情報のない隔離サンドボックスで新しいクローンを使い、無制限のインターネットや本番ネットワークに接続しない。結果はgitワークツリーの外の非公開の場所に置く（スキャン結果にはソース抜粋や脆弱性の詳細が含まれ得る）。無関係な認証情報は先に取り除く。Codex Security CLIは「OSの権限で動き、承認のために止まらない」。
4. **権限。** 最小権限のCodex権限プロファイル（編集不要なら `:read-only`）、`approval_policy = "on-request"`、`approvals_reviewer = "auto_review"`、プロキシ機能で強制するネットワーク許可リストを、推奨構成のとおり使う。`:danger-full-access` と `--yolo` は避ける。リポジトリ・Issue・文書・ツール出力にある指示は信頼せず、範囲を広げられない。
5. **スキャンとトリアージ。** Codex Securityのプラグイン、CLI、SDKを使う（CLIとSDKは公開パッケージ `@openai/codex-security`。OpenAI推論を使うスキャンにはCodex Securityアクセスが必要で、リポジトリ全体のスキャンにはTrusted Access for Cyberも必要な場合がある）。まず `--dry-run` で対象と出力先を確認する。所見は根拠と影響で順位付けし、モデルだけの主張は未検証と表示する。
6. **検証。** 重要な所見は、報告前に独立に検証する（テスト、静的解析、本リポジトリのレビュー規約に沿った別providerのレビュー）。報告の判断は人が持つ。PoCを行う場合も隔離コピー内に限り、認証情報・永続化・外部システムの手前で止める。
7. **開示。** プロジェクトのセキュリティポリシーと協調的開示に従う。未修正の詳細は、この公開リポジトリ、Issue、PRに載せない。修正パッチの共有は、保守者が同意した場合に限る。
8. **ログと停止。** リクエスト、ツール呼び出し、ネットワークのログをエージェント環境の外に置く。監視やレビュアーが失敗したら止める（fail closed）。終了後は一時的な認証情報を失効し、バックグラウンドプロセスを終了し、環境を破棄する。
9. **記録。** 公開するのは一般化したメモのみ：未修正問題の所見、アカウント識別子、スクリーンショット、残高は載せない。到達段階（文書化／設定済み／実行済み／検証済み）を正直に記録する。

## 3. 既存方針との関係

- 定常のモデル選択（GPT-6 Luna／Sol Medium、Astraは例外）とMiMo-V2.6-Proレビュー標準は変更しない。Daybreakは認可されたセキュリティ作業のみが対象で、定常レビューには使わない。
- レビューの分離は変わらない：実装担当のツールは独立レビュアーに数えず、現headの証拠を使う。
- Qwen・RunPodの状態、TLS、権限、有料操作は変更しない。Trusted Accessの申請やAPIリクエストは、別の承認と別の変更になる。

## 4. 未確認点

- 本プロジェクトまたは本人がDaybreakアクセスを持つか、申請するか：**未決定**。
- 1.2の名称の違いと、Lunaの対象可否。
- 料金、レート制限、OSS保守者向けのCodex Security適格条件、および取得できなかったページ（Daybreakのトラブルシューティング、OpenAIの発表ページとヘルプセンターは直接取得でHTTP 403。Codex for OSSプログラムは読んだ文書で言及のみ）。
- 日付：文書ページに日付表示はない。

## 5. 出典

- Models and Trusted Access: https://learn.chatgpt.com/docs/cyber-safety
- Recommended configuration: https://learn.chatgpt.com/codex/cyber-safety/recommended-configuration
- Use Daybreak in the Responses API: https://developers.openai.com/api/docs/guides/daybreak
- Cybersecurity checks（API）: https://developers.openai.com/api/docs/guides/safety-checks/cybersecurity
- Codex Security: https://learn.chatgpt.com/codex/security 、CLIクイックスタート: https://learn.chatgpt.com/codex/security/cli
- Codex open source（Codex for OSSプログラムの言及）: https://learn.chatgpt.com/codex/open-source
- 補助（名称の違いの確認のみ）：検索で見つかったXのOpenAI投稿と報道（上記の規則には使っていない）。
