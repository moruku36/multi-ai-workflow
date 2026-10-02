# AIチーム運用決定 — 2026-10-02

[English](operating-decisions-2026-10-02.md) | [日本語](operating-decisions-2026-10-02.ja.md)

今回の運用方針を記録します。下記のCLI観測は所有者の運用セッションから報告されたもので、この文書更新で再実行していません。方針の承認、コマンドの受理、実行、検証は別の事実として扱います。

## 役割とモデル選択

| 担当 | 責任 |
|---|---|
| Dottie | PM / オーケストレーター。範囲、担当、引き継ぎ、利用枠、証跡を管理 |
| Chappy | アーキテクト / 独立レビュアー。OpenAI側の調査・文章作成・明示的に割り当てたCodex作業も継続 |
| Claude | コーディング・デプロイの標準担当。Sonnetを標準とし、デプロイには適用される承認が必要 |
| Gemini / Antigravity | PoC・モック・初期実装。同じ成果物をClaudeへ引き継ぐ |
| Qwen | マルチモーダル作業・調査。ローカルのテキスト環境とColabの機能を区別 |

通常の**Codex**文章作成・コーディングはLuna / Lowから始め、必要な場合だけ既存のLuna Medium → Luna High → Sol Mediumへ上げます。これはCodexを使うときのモデル方針であり、全コーディングをCodexに割り当てる指示ではありません。ユーザーの担当指定を優先し、既存実装を再利用します。

**蒸留とFactory**では、所有者が**初期調査・論文解釈にAstraを使うことを明示的に許可**しています。Solで十分なら効率的なSolを使います。この例外は、全タスクのAstra標準化や通常コーディングの昇格方針の置き換えではありません。ClaudeはSonnetが標準で、Opusは難しい仕事に限ります。既存のバージョン付きモデル名は所有者申告のスナップショットであり、実行時モデルの証明や新たなAPI識別子ではありません。

既存の難問向けAstra経路は、Solで不足し、必要性を個別判断する場合に、従来の許可範囲で維持します。通常のCodex昇格順とは分離し、自動的な次段階とは扱いません。調査例外は従来の用途を禁止するものでも、全タスクのAstra利用を許可するものでもありません。

**Gemini effortの差異:** 既存文書は通常High、残量が少ない場合にリセット時刻と難度を見てMediumとしています。現在の所有者の希望はMediumです。今回の作業ではこの希望を記録し、既存方針との違いを明示します。全Geminiタスクを無断でMediumへ統一せず、既存High方針を現在の希望とも扱いません。タスクごとの指定effortと実行時の観測値を別々に記録します。

## 比較と証跡の契約

モデル比較の前に、同じ入力成果物、プロンプト、受入条件、評価基準、制約、評価手順を固定します。比較実行前に成果物manifestを作成します。条件を変えた場合は新しい比較として扱い、異なる条件の結果を混ぜません。

最小manifest項目:

```text
task_id / comparison_id:
input_revision / paths / content_hashes:
prompt_revision / rubric_revision / acceptance_criteria:
provider / route / CLI_version / environment:
requested_model / requested_effort:
observed_runtime_model / observed_runtime_effort: 証跡がなければUNKNOWN
accepted: 状態 / 受理証跡参照
executed: 状態 / 実行証跡参照
verified: 状態 / 検証証跡参照
output_paths / content_hashes:
review_findings / verification_results / unresolved_items:
reacquire_source / revision_or_hash:
```

指定モデル・effortは実行時モデル・effortの証明ではありません。実行時の証跡がない場合は`UNKNOWN`とし、役割・別名・指定・OK応答から識別子を推測しません。`accepted`（受理）、`executed`（実行）、`verified`（検証）を分けます。キュー受領票は受理だけを示します。結果を読み、受入条件を検証してから完了と報告します。公開するのはサニタイズしたmanifestと証跡参照だけで、非公開セッション内容は含めません。

## 報告されたCLI検証の境界

| 経路 | 報告済みの証跡 | 未検証の範囲 |
|---|---|---|
| Claude、Macの既存クラウドセッション | CLIによる実際の送信は検証済み | Windows経路の証明にはならない |
| Claude、Windows 2.1.287 | 構文に対応。ローカルSonnetのツール不使用OKテスト成功 | Windowsから既存クラウドセッションへの実送信は未実施。キュー受領票は結果の読み取りではない |
| Antigravity、Windows 1.2.14 | 指定`gemini-3.8-flash-medium`のツール不使用OKテスト成功。headless JSON・timeout・conversation機能が利用可能 | 同等のクラウドセッション経路は未確認。指定名だけでは実行時モデルやコード・ツール実行を証明しない |

これらの限定的なテストは、デプロイ、リポジトリ編集、無人実行、自動統合全体の成立を証明しません。この文書更新のための追加の有料・モデル実行は不要です。

## Windows拠点とFactoryの次工程

Windowsは常時稼働のローカル拠点として使う予定です。**2026-10-02時点の報告:** Windows wrapper（task7）は試作実装済みで、**オフライン14テストが成功**しています。ただし、wrapper経由の実接続テストは**未実施**です。Antigravity wrapperは、呼び出し単位のツール範囲制御が対応していることの検証待ちで保留中です。これは日付付きの実装・検証状況であり、製品一般の制限ではありません。これらは所有者の運用セッションからの報告で、この文書更新では再実行していません。DottieのクラウドPM機能、CodexBarルーティング、ローカルエージェントadapterは既存の統合検証が必要で、完全自動化済みとは扱いません。

**Factoryの最小manifest / review / reacquire方針は実装承認済み**ですが、成立は未検証です。上記manifestから始め、固定した評価基準に照らして成果物と指摘をレビューし、入力・出力の再取得用に出典・revision・hashを残します。成果物が欠けたら再取得・再検証し、記憶から再構成しません。実装方針の承認と、実装成功・全体検証成功を区別します。

## 公開文書の範囲

秘密情報、認証情報、個人の健康情報、企業メール、非公開メモを含めません。今回の許可は文書更新のみで、インストール、セキュリティ・認証・設定変更、有料利用、自動デプロイは行いません。push・PR作成・mergeの前にローカル差分とチェック結果を報告します。
